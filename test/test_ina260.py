from semubot_raspberry_bringup.battery_monitor import (
    cell_voltage_to_percentage, raw_to_volts)


def test_conversions():
    assert abs(raw_to_volts(bytes([0x25, 0x80])) - 12.0) < 1e-9   # 9600 * 1.25 mV


def test_percentage_7s():
    assert cell_voltage_to_percentage(29.4 / 7) == 1.0
    assert cell_voltage_to_percentage(21.4 / 7) == 0.0
    assert abs(cell_voltage_to_percentage(23.6 / 7) - 0.0857) < 1e-3   # ~9 %
    assert cell_voltage_to_percentage(30.0 / 7) == 1.0
    assert cell_voltage_to_percentage(18.0 / 7) == 0.0
    assert abs(cell_voltage_to_percentage(3.80) - 0.60) < 1e-9   # 26.6 V, between table points
