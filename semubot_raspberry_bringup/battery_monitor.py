import collections

import lgpio
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState

# Voltage only: the INA260 sits on a thin wire from battery + to Vin+, Vin- unconnected.
# The motors can pull far more than its 15 A rating, so it must NOT go in the main power line.
REG_VOLTAGE = 0x02  # INA260 bus voltage, 16-bit big-endian, 1.25 mV/LSB

# Li-ion resting voltage per cell -> charge, straight lines in between
# ponytail: rough generic NMC curve, fine for a display; measure your pack if it reads off
CELL_CURVE = [(21.4 / 7, 0.0), (3.30, 0.05),  # 0 % at the pack's 21.4 V minimum
                (3.50, 0.15), (3.70, 0.45), (3.90, 0.75), (4.20, 1.0)]


def raw_to_volts(raw: bytes) -> float:
    return int.from_bytes(raw, 'big') * 0.00125


def cell_voltage_to_percentage(volts: float) -> float:
    if volts <= CELL_CURVE[0][0]:
        return 0.0
    for (v0, p0), (v1, p1) in zip(CELL_CURVE, CELL_CURVE[1:]):
        if volts <= v1:
            return p0 + (p1 - p0) * (volts - v0) / (v1 - v0)
    return 1.0


class BatteryMonitor(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        bus = self.declare_parameter('i2c_bus', 1).value
        addr = self.declare_parameter('i2c_address', 0x40).value
        rate = self.declare_parameter('rate_hz', 2.0).value
        # Calibration knobs: compare against a multimeter and adjust
        self.voltage_scale = self.declare_parameter('voltage_scale', 1.0).value
        self.cells = self.declare_parameter('cells', 7).value
        # Average ~30 s of readings so motor load sag doesn't make the percentage jump
        self.recent = collections.deque(maxlen=max(1, int(30 * rate)))

        self.h = lgpio.i2c_open(bus, addr)
        self.pub = self.create_publisher(BatteryState, '/semubot/battery', 10)
        self.create_timer(1.0 / rate, self.tick)
        self.get_logger().info(f'Reading INA260 on i2c-{bus} @ {hex(addr)}')

    def read(self, reg):
        _, data = lgpio.i2c_read_i2c_block_data(self.h, reg, 2)
        return bytes(data)

    def tick(self):
        try:
            volts = raw_to_volts(self.read(REG_VOLTAGE)) * self.voltage_scale
        except lgpio.error as e:
            self.get_logger().warning(f'INA260 read failed: {e}', throttle_duration_sec=5.0)
            return

        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = volts
        msg.current = float('nan')  # not measured
        msg.present = True
        msg.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_LION
        self.recent.append(volts)
        average = sum(self.recent) / len(self.recent)
        msg.percentage = cell_voltage_to_percentage(average / self.cells)  # 0.0-1.0
        self.pub.publish(msg)

    def destroy_node(self):
        lgpio.i2c_close(self.h)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
