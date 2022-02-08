#!/bin/bash


[ "$UID" -eq 0 ] || exec sudo bash "$0" "$@"

var=$(date +"%FORMAT_STRING")
now=$(date +"%m_%d_%Y")
NOW=$(date +%Y-%m-%d-%H%M%S)
printf "%s\n" $now
today=$(date +"%Y-%m-%d")

candump any -D -l > "/home/pi/logs/${NOW}.log"
