# semubot_raspberry_bringup


ROS 2 (Jazzy) bringup package for the SemuBot wheelbase's Raspberry Pi 5. Launches motor control and joystick teleop together as a single system.

* Installed as semubot_raspberry_bringup.service

## Configuration

The launch takes its parameters from the robot profile in `semubot_bringup`, `config/profiles/<profile>.yaml`, sections `cmd_vel_motor_driver`, `battery_monitor`, `joy_node` and `teleop_twist_joy`. The profile is `SEMUBOT_PROFILE` from the environment, `v1` by default, or the `profile` launch argument. A missing profile stops the launch.

```bash
ros2 launch semubot_raspberry_bringup drive.launch.py profile:=v1
```
