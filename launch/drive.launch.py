from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='semubot_raspberry_bringup',
            executable='cmd_vel_motor_driver',
            name='cmd_vel_motor_driver',
            output='screen',
        ),

        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
        ),

        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy',
            output='screen',
            parameters=[{
                'enable_button': 7,

                'axis_linear.x': 1,
                'scale_linear.x': 0.5,

                'axis_linear.y': 0,
                'scale_linear.y': 0.5,

                'axis_angular.yaw': 2,
                'scale_angular.yaw': 0.8,
            }]
        ),
    ])
