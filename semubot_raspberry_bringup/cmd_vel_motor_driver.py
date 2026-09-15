import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
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

        print('Listening for messages on ROS topic /cmd_vel')

    def listener_callback(self, msg):
        x = msg.linear.x
        y = msg.linear.y
        z = msg.angular.z

        print(f'Received message to move x: {x} y: {y} z: {z}')

        direction = np.array([-y, x, z])
        result = np.dot(self.matrix, direction)

        for i, vel in enumerate(result):
            vel = -vel
            duty = min(max(abs(vel * 100), 0), 100)

            lgpio.gpio_write(self.h, self.dir_pins[i], 0 if vel < 0 else 1)
            lgpio.tx_pwm(self.h, self.pwm_pins[i], self.pwm_freq, duty)

    def destroy_node(self):
        for pin in self.pwm_pins:
            lgpio.tx_pwm(self.h, pin, self.pwm_freq, 0)
        lgpio.gpiochip_close(self.h)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelMotorDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except OSError as e:
        self.get_logger().warning(F"Network unavailable: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
