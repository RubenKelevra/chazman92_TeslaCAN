#!/bin/bash

#canplayer vcan0=can1 vcan1=can0 -l i -I /home/pi/logs/savvydump.log
echo Logfiles are played from /home/pi/logs
search_dir=/home/pi/logs
yourfilenames=`ls $search_dir/*.log`

#kill any running mqttpy.py instances
kill $(pgrep -f 'mqttpy.py')

echo
read -p 'Run mqttpy.py? (Y) ' runmqtt

if [[ $runmqtt == "Y" ]]
then
  nohup python3 /home/pi/scripts/mqttpy.py &
  echo
  echo myttpy RUNNING in background to kill use PID
  ps ax | grep mqttpy.py
else
  echo
  echo NOT running mqttpy.py
fi

for eachfile in $yourfilenames
do
   echo $eachfile
done
echo
read -p 'Logfile Name: ' logfile
read -p 'Number of loops: (1,2,(i)nfinite: ' loops
read -p 'SavvyCan Format (S) or RAW Candump (any):' format

bus=""
if [[ $format == "S" ]]
then
  bus=""
else
  bus="vcan0=can1 vcan1=can0"
fi
echo
echo running command - canplayer $bus -l $loops -I /home/pi/logs/$logfile

canplayer $bus -l $loops -I /home/pi/logs/$logfile

echo
read -p 'Kill mqttpy.py processes? (Y) ' killmqtt
if [[ $killmqtt = "Y"]]
then
  kill $(pgrep -f 'mqttpy.py')
  echo mqttpy.py should have been killed
fi