#!/bin/bash

#canplayer vcan0=can1 vcan1=can0 -l i -I /home/pi/logs/savvydump.log
echo Logfiles are played from /home/pi/logs
search_dir=/home/pi/logs
yourfilenames=`ls $search_dir/*.log`
for eachfile in $yourfilenames
do
   echo $eachfile
done
echo
read -p 'Logfile Name: ' logfile
read -p 'Number of loops: (1,2,(i)nfinite: ' loops
read -p 'SavvyCan Format (S) or RAW Candump (C):' format

bus=""
if [[ $format == "S" ]]
then
  bus=""
else
  bus="vcan0=can1 vcan1=can0"
fi
echo
echo  playing canplayer $bus -l $loops -I /home/pi/logs/$logfile

canplayer $bus -l $loops -I /home/pi/logs/$logfile
