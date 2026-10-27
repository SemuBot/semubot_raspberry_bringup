import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float32
import lgpio
import numpy as np

CHIP = 4  # Pi 5 uses gpiochip4

class CmdVelMotorDriver(Node):
    def __init__(self):
        super().__init__('cmd_vel_motor_driver')
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.listener_callback,
            10)
        # Speed multiplier set from the chest display, latched so a restart gets the last value
        self.speed_scale = 1.0
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Float32, '/semubot/speed_scale', self.speed_scale_callback, latched)

        self.estop_subscription = self.create_subscription(
            Bool,
            '/emergency_stop',
            self.estop_callback,
            10)
        self.h = lgpio.gpiochip_open(CHIP)
        self.pwm_pins = [13, 19, 12]   # Right, Left, Back
        self.dir_pins = [6, 26, 5]     # Right, Left, Back
        self.pwm_freq = 1000

        for pin in self.pwm_pins:
            lgpio.gpio_claim_output(self.h, pin)
            lgpio.tx_pwm(self.h, pin, self.pwm_freq, 0)

        for pin in self.dir_pins:
            lgpio.gpio_claim_output(self.h, pin)

        self.matrix = np.array([
            [-0.33,  0.58, 0.33],
            [-0.33, -0.58, 0.33],
            [ 0.67,  0.0,  0.33]
        ])

        # Stop the motors if /cmd_vel goes quiet (lost stop message, dead webapp, network drop).
        # Senders repeat every ~120 ms while driving; raise this if WiFi jitter causes stutter.
        self.cmd_vel_timeout = self.declare_parameter('cmd_vel_timeout', 0.5).value
        self.last_cmd_time = time.monotonic()
        self.moving = False
        # After an emergency stop, ignore /cmd_vel until a zero command (joystick released)
        self.estopped = False
        self.create_timer(0.1, self.watchdog)

        print('Listening for messages on ROS topic /cmd_vel')

    def speed_scale_callback(self, msg):
        self.speed_scale = min(max(msg.data, 0.1), 1.0)
        print(f'Speed scale set to {self.speed_scale:.1f}')

    def stop_motors(self):
        for pin in self.pwm_pins:
            lgpio.tx_pwm(self.h, pin, self.pwm_freq, 0)
        self.moving = False

    def watchdog(self):
        if self.moving and time.monotonic() - self.last_cmd_time > self.cmd_vel_timeout:
            self.get_logger().warning(f'No /cmd_vel for {self.cmd_vel_timeout}s, stopping motors')
            self.stop_motors()

    def estop_callback(self, msg):
        if msg.data:
            self.estopped = True
            self.stop_motors()
            self.get_logger().warning('Emergency stop: motors off until a zero /cmd_vel is received')

    def listener_callback(self, msg):
        x = msg.linear.x * self.speed_scale
        y = msg.linear.y * self.speed_scale
        z = msg.angular.z * self.speed_scale

        print(f'Received message to move x: {x} y: {y} z: {z}')

        self.last_cmd_time = time.monotonic()
        if self.estopped:
            if x == 0 and y == 0 and z == 0:
                self.estopped = False
                self.get_logger().info('Emergency stop released')
            return

        direction = np.array([-y, x, z])
        result = np.dot(self.matrix, direction)

        for i, vel in enumerate(result):
            vel = -vel
            duty = min(max(abs(vel * 100), 0), 100)

            lgpio.gpio_write(self.h, self.dir_pins[i], 0 if vel < 0 else 1)
            lgpio.tx_pwm(self.h, self.pwm_pins[i], self.pwm_freq, duty)
        self.moving = True

    def destroy_node(self):
        self.stop_motors()
        lgpio.gpiochip_close(self.h)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelMotorDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except OSError as e:
        node.get_logger().warning(F"Network unavailable: {e}")
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
