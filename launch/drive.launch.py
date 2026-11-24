import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def check_profile(context, profile_file):
    path = profile_file.perform(context)
    if not os.path.isfile(path):
        raise RuntimeError(f'Profile not found: {path}')


def generate_launch_description():
    profile_file = PathJoinSubstitution([
        FindPackageShare('semubot_bringup'),
        'config',
        'profiles',
        [LaunchConfiguration('profile'), '.yaml'],
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'profile',
            default_value=EnvironmentVariable('SEMUBOT_PROFILE', default_value='v1'),
            description='Robot profile from semubot_bringup/config/profiles',
        ),
        OpaqueFunction(function=check_profile, args=[profile_file]),

        Node(
            package='semubot_raspberry_bringup',
            executable='cmd_vel_motor_driver',
            name='cmd_vel_motor_driver',
            parameters=[profile_file],
            output='screen',
        ),

        Node(
            package='semubot_raspberry_bringup',
            executable='battery_monitor',
            name='battery_monitor',
            parameters=[profile_file],
            output='screen',
        ),

        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[profile_file],
            output='screen',
        ),

        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy',
            parameters=[profile_file],
            output='screen',
        ),
    ])
