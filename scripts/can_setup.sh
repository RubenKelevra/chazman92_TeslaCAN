#!/bin/bash

# /etc/systemd/system/load_can_ifaces.service

# [Unit]
# Description=Systemd service for creating vcan0, can0, can1  at startup
# [Service]
# ExecStart=/home/pi/scripts/can_setup.sh
# [Install]
# WantedBy=network.target

# run .. sudo systemctl enable load_can_ifaces.service


# Make sure the script runs with super user priviliges.
[ "$UID" -eq 0 ] || exec sudo bash "$0" "$@"
# Load the kernel module.
modprobe vcan
# Create the virtual CAN interface.
ip link add dev vcan0 type vcan
ip link add dev vcan1 type vcan
# Bring the virutal CAN interface online.
ip link set up vcan0
ip link set up vcan1

# Setup can0 and can1
#ip link set can0 up type can bitrate 500000 listen-only on
#ip link set can1 up type can bitrate 500000 listen-only on
ip link set can0 up type can bitrate 500000
ip link set can1 up type can bitrate 500000
