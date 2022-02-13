#!/bin/bash

echo Can files are converted from /Users/chuckcook/Data Drive/TeslaVideos/CanLogs

yourfilenames=`ls /Users/chuckcook/Data\ Drive/TeslaVideos/CanLogs/*.log`
for eachfile in $yourfilenames
do
   echo $eachfile
done
echo
read -p 'Logfile Name to Convert: ' logfile
read -p 'Output Filename: ' outputFilename
echo
echo  Converting logfile to ASC $logfile

python3  /Users/chuckcook/Data\ Drive/TeslaVideos/CanLogs/scripts/convertbinary.py /Users/chuckcook/Data\ Drive/TeslaVideos/CanLogs/$logfile /Users/chuckcook/Data\ Drive/TeslaVideos/CanLogs/$outputFilename
