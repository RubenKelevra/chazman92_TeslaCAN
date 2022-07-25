CANServer_address = "192.168.1.48"
#CANServer_address = "canserver.local"
#Filter applied to conversion
msgIDs = [0x04F, 0x101, 0x108, 0x111, 0x118, 0x129, 0x145, 0x257, 0x318, 0x399, 0x3B6]

import json 
from urllib import request, parse, error
import struct
import datetime
import time

import sys
import os.path

def convertRawtoASC(inputFilename, outputFilename):
    original_stdout = sys.stdout
    
    with open(inputFilename, mode='rb') as file:
        
        #File header should be 22 bytes
        headerData = file.read(22)
        if (len(headerData) == 22):
            #Check to see if our header matches what we expect        
            if (headerData == b'CANSERVER_v2_CANSERVER'):
                #all is well

                #open the output file
                outputfile = open(outputFilename, mode='w')
                sys.stdout = outputfile

                pass
            else:
                print("Not a valid CANServer v2 file.  Unable to convert", file=sys.stderr)
                exit(1)

        while True:
            #Look for the start byte
            byteRead = file.read(1)
            if len(byteRead) == 1:
                if (byteRead == b'C'):
                    #check to see if we have a header.
                    goodheader = False
                    
                    #read 21 more bytes
                    possibleHeader = file.read(21)
                    if (len(possibleHeader) == 21):
                        if (possibleHeader == b'ANSERVER_v2_CANSERVER'):
                            #we found a header (this might have been because of just joining multiple files togeather)
                            #we can safely skip these bytes
                            goodheader = True
                            pass


                    if (goodheader):
                        #header was valid.  Just skip on ahead
                        pass
                    else:
                        #we didn't see the header we expected.  Seek backwards the number of bytes we read
                        file.seek(-len(possibleHeader), 1)                    
                elif (byteRead == b'\xcd'):
                    #this is a mark message.  The ASC format doesn't seem to have any comments or anything so we can't directly convert this mark
                    #Instead we create a new output file with the markstring as part of its filename
                    marksize = file.read(1)
                    marksize = int.from_bytes(marksize, 'big')
                    markdata = file.read(marksize)

                    markString = markdata.decode("ascii")
                    
                    #lets switch to a new file named based on the mark
                    splitOutputFilename = os.path.splitext(outputFilename)
                    newOutputFilename = splitOutputFilename[0] + "-" + markString + splitOutputFilename[1]
                    
                    outputfile.close()
                    
                    outputfile = open(newOutputFilename, mode='w')
                    sys.stdout = outputfile

                elif (byteRead == b'\xce'):
                    #this is running time sync message.
                    timesyncdata = file.read(8)

                    if len(timesyncdata) == 8:
                        lastSyncTime = struct.unpack('<Q', timesyncdata)[0]
                    else:
                        print("Time Sync frame read didn't return the proper number of bytes", file=sys.stderr)

                elif (byteRead == b'\xcf'):
                    #we found our start byte.  Read another 5 bytes now
                    framedata = file.read(5)
                    if len(framedata) == 5:
                        unpackedFrame = struct.unpack('<2cHB', framedata)

                        frametimeoffset = int.from_bytes(unpackedFrame[0] + unpackedFrame[1], 'little')
                        #convert the frametimeoffset  from ms to us
                        frametimeoffset = frametimeoffset * 1000

                        frameid = unpackedFrame[2]

                        framelength = unpackedFrame[3] & 0x0f
                        busid = (unpackedFrame[3] & 0xf0) >> 4
                        if (framelength < 0):
                            framelength = 0
                        elif (framelength > 8):
                            framelength = 8

                        framepayload = file.read(framelength)

                        frametime = lastSyncTime + frametimeoffset

                        #if frameId in list download
                        if frameid in msgIDs:  #msgIDs Array in Global variables for filter
                            print("({0:017F})".format(frametime/1000000), end='')
                            print(" can%d " % (busid), end='')
                            print("{0:03X}#".format(frameid), end='')
                            for payloadByte in framepayload:
                                print("{0:02X}".format(payloadByte), end='')
                            print("")

                    else:
                        break
            else:
                break
                    
    if (outputfile):
        outputfile.close()
    sys.stdout = original_stdout
    return

sleepTime = 60
print("Looking for CANServer")
while True:
    #check to see if the server exists
    try:
        status = request.urlopen("http://" + CANServer_address + "/stats")

        print("CANServer alive.  Looking for files...")

        #if we got a response lets try and load the files list
        filesToDownload = []
        activeFileName = ""
        with request.urlopen("http://" + CANServer_address + "/logs/load") as url:
            data = json.loads(url.read().decode())
            activeFileName = data['activefile']

        offsetToFetchFrom = 0
        while (True):
            moreToFetch = False
            with request.urlopen("http://" + CANServer_address + "/logs/files?offset=" + str(offsetToFetchFrom)) as url:
                data = json.loads(url.read().decode())
                for filedata in data:   
                    if (filedata['n'] == activeFileName):
                        #ignore this file.  Its activly being logged to
                        pass
                    else:
                        if (filedata['n'] == '---cont---'):
                            moreToFetch = True
                            offsetToFetchFrom = filedata['s']
                        else:
                            filesToDownload.append(filedata['n'])

            if (moreToFetch == False):
                #We didn't get a new offset to fetch from, so we are all done
                break

        filesToDownload.sort()
        
        print("Found %d files..." % (len(filesToDownload)))
        #exit(0)
        
        for fileToDownload in filesToDownload:
            downloadURL = "http://" + CANServer_address + "/logs/files/download?id=" + fileToDownload
            try:
                print("Downloading: " + fileToDownload + "...")
                #update autoDownloadPath for location
                #autoDownloadPath = '/Users/chuckcook/Data Drive/TeslaVideos/CanLogs/AutoDownloads/'  #MAC Path
                autoDownloadPath = '/home/pi/logs/autodownloads/'  #TeslaCan Path
                autoDownloadFilename = autoDownloadPath + datetime.datetime.now().strftime("%Y-%m%d-%H%M") + "-" + fileToDownload
                
                #convertedFilename = autoDownloadPath + "converted/" + datetime.datetime.now().strftime("%Y-%m%d-%H%M") + "-converted_" + fileToDownload
                filename, headers = request.urlretrieve(downloadURL, autoDownloadFilename)

                #download completed. 
                # Delete the file from server
                data = parse.urlencode({ 'id': fileToDownload }).encode()
                req =  request.Request("http://" + CANServer_address + "/logs/files/delete", data=data)
                resp = request.urlopen(req)

            except error.URLError as e:
                #print(autoDownloadFilename)
                #print(downloadURL)
                print("Error downloading: " + fileToDownload)

            #ConvertASC
            try:
                #create converted filepath
                convertedFilename = autoDownloadPath + "converted/%b%d/" + datetime.datetime.now().strftime("%m%d-") + "converted_" + fileToDownload

                print ("Converting file ...")
                convertRawtoASC(autoDownloadFilename, convertedFilename)
                print ("File Converted ...")

            except:
                # print("Error converting to ASC")
                e = sys.exc_info()[0]
                print( "Error: %s" % e )

        print ("Sleeping 60 seconds")
        sleepTime = 60

    except error.URLError as e:
        #server isn't out there.
        sleepTime = 30
        pass

    time.sleep(sleepTime)