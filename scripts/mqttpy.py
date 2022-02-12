# TODO
# Calculate interventions when AP is engaged and accelerator is pressed
# Find blinker Data to use in interventions


# Created by Chuck Cook on Jan 28 2022

import os
from paho.mqtt import client as mqtt_client
import time  # The time library is useful for delays
from datetime import datetime
import calendar
import random
import can  # Python-can tools
import cantools

import csv


# can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan_ctypes')# socketcan_native
# can1 = can.interface.Bus(channel = 'can1', bustype = 'socketcan_ctypes')# socketcan_native

# load DBC File
db = cantools.database.load_file('/home/pi/scripts/Model3CAN.dbc')

broker = 'localhost'
port = 1883
topic = "ui"

# timestamps
timestamp_3B6 = time.time()
# currentOdometer = 0
# ApEngagedTripStartOdometer = None
# #ApTripLength = 0
ApDisengageCounter = 0
ApInterveneCounter = 0
ApEngaged = False
DriverAcceleratorPressed = False
ApInterveneActive = False


try:
    bus = can.interface.Bus(channel='', bustype='socketcan_ctypes')
    canReader = can.BufferedReader()
#    canLogger =can.Logger(str_current_datetime + '_pycan.log')
    canNotifier = can.Notifier(bus, [canReader])
    #canNotifier = can.Notifier(bus, [canReader, canLogger])

    print('Connected to generic bus')
except OSError:
    print('Cannot find generic bus')

bus.set_filters([
                # {"can_id":0x04F, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x101, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x108, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x111, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x118, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x129, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x145, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x257, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x318, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x399, "can_mask": 0xFFFFFFF, "extended": False},
                {"can_id": 0x3B6, "can_mask": 0xFFFFFFF, "extended": False}
                ])


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def listenToCan(client):
    try:
        while True:
            msg = canReader.get_message()
            #print(msg)
            try:
                messageID = msg.arbitration_id
                # elif messageID == 0x04F:
                #     GPSLatLong(client, msg)
                if messageID == 0x101:
                    RCM_inertial1(client, msg)

                elif messageID == 0x108:
                    DirTorque(client, msg)

                elif messageID == 0x111:
                    RCM_inertial2(client, msg)

                elif messageID == 0x118:
                    DriveSystemStatus(client, msg)

                elif messageID == 0x129:
                    SteeringAngle(client, msg)

                elif messageID == 0x145:
                    ESP_status(client, msg)

                elif messageID == 0x257:
                    DIspeed(client, msg)

                elif messageID == 0x318:
                    SystemTimeUTC(client, msg)

                elif messageID == 0x399:
                    # can1 sending short data, so eliminating those messages
                    if ((msg.channel == 'vcan0') or (msg.channel == 'can0')):
                        DAS_statusclient(client, msg)

                elif messageID == 0x3B6:
                    global timestamp_3B6
                    # only update odometer every second
                    if getTimeDelayed(timestamp_3B6, 1):
                        Odometer(client, msg)
                        timestamp_3B6 = time.time()
                else:
                    print("Message {:03X} not handled".format(messageID))
                    pass
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print(message)
    except KeyboardInterrupt:
        # Catch keyboard interrupt
        print('\n\rKeyboard interrtupt')


def publish_mqtt(client, mqtt_topic, mqtt_message):
    #global msg_count
    # print(timeDelta)

    result = client.publish(mqtt_topic, mqtt_message)
    status = result[0]

    if status == 0:
        pass
        # print(f"{decoded}`")
        #msg_count += 1
        # return(f"Sent message to topic {topic}")
    else:
        print(f"Failed to send message to topic {topic}")

    return


def GPSLatLong(client, msg):
    # BO_ 79 ID04FGPSLatLong: 8 ChassisBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)

    publish_mqtt(client, topic + "/gps_lat",
                 "{:.1f}".format(decoded['GPSLatitude04F']))
    publish_mqtt(client, topic + "/gps_lon",
                 "{:.1f}".format(decoded['GPSLongitude04F']))

    return


def DriveSystemStatus(client, msg):
    # BO_ 79 ID04FGPSLatLong: 8 ChassisBus
    localDict = {'DI_GEAR_D': 'D', 'DI_GEAR_P': 'P',
                 'DI_GEAR_R': 'R', 'DI_GEAR_SNA': 'SNA'}

    global DriverAcceleratorPressed, ApInterveneActive
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)
#print (DriverAcceleratorPressed, ApInterveneActive, decoded['DI_accelPedalPos'])
    if (decoded['DI_accelPedalPos'] == 0.0):
        DriverAcceleratorPressed = False
        if (ApInterveneActive == True):
            ApInterveneActive = False
    else:
        DriverAcceleratorPressed = True

    publish_mqtt(client, topic + "/accel-pedal-posn",
                 "{:.0f}".format(decoded['DI_accelPedalPos']))

    publish_mqtt(client, topic + "/gear-posn",
                 "{}".format(translateResponse(localDict, decoded['DI_gear'])))

    return


def RCM_inertial1(client, msg):
    # BO_ 257 ID101RCM_inertial1: 8 ChassisBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)
    # if timeDelta > .02:
    publish_mqtt(client, topic + "/pitch_rate",
                 "{:.2e}".format(decoded['RCM_pitchRate']))
    publish_mqtt(client, topic + "/roll_rate",
                 "{:.2e}".format(decoded['RCM_rollRate']))
    publish_mqtt(client, topic + "/yaw_rate",
                 "{:.2e}".format(decoded['RCM_yawRate']))
    return


def DirTorque(client, msg):
    # BO_ 264 ID108DIR_torque: 8 VehicleBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)

    publish_mqtt(client, topic + "/rear_torq",
                 "{:.0f}".format(decoded['DIR_torqueActual']))
    publish_mqtt(client, topic + "/axel_speed",
                 "{:.0f}".format(decoded['DIR_axleSpeed']))
    # publish_mqtt(client, topic + "/pedal_posn",
    #              "{:.1f}".format(decoded['DIR_slavePedalPos']))

    return


def RCM_inertial2(client, msg):
    # BO_ 273 ID111RCM_inertial2: 8 ChassisBus
    try:

        decoded = db.decode_message(msg.arbitration_id, msg.data)
        # print(decoded)
        decodedLatAccel = decoded['RCM_lateralAccel'] * \
            0.101972  # Convert m/s^2 to Gs
        # Convert m/s^2 to Gs
        decodedLongAccel = decoded['RCM_longitudinalAccel'] * 0.101972
        # Convert m/s^2 to Gs
        decodedVertAccel = decoded['RCM_verticalAccel'] * 0.101972

        publish_mqtt(client, topic + "/custom_accel", "{:.3f}".format(decodedLatAccel) + ";" + "{:.3f}".format(
            decodedLongAccel) + ";" + "{:.3f}".format(decodedVertAccel) + ";#FFFF00")  # Yellow

        #publish_mqtt(client, topic + "/vert_accel", "{:.1f}".format(decoded['RCM_verticalAccel']))

        # Log Lat and Long Acceleration data in g's - False is without Timestamp
        #logMessage("testLog.log", '{"lat": %0.3f}, {"long": %1.3f}, {"vert": %2.3f},' %(decodedLatAccel, decodedLongAccel, decodedVertAccel), False)

        # publish_mqtt(client, topic + "/custom_lon-accel",
        #             "{:.1f}".format(decodedLongAccel) + ";#FFFF00")

        #writer.writerow({'timestamp': time.time(), 'label': 'lon-accel', 'value': decodedLongAccel})

    except Exception as ex:
        template = " RCM Inertial exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
    return


def SteeringAngle(client, msg):
    # BO_ 297 ID129SteeringAngle: 8 VehicleBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)

    decodedSteeringAngle = decoded['SteeringAngle129']

    publish_mqtt(client, topic + "/steering-angle",
                 "{:0.1f}".format(decodedSteeringAngle))
    return


def ESP_status(client, msg):
    # BO_ 325 ID145ESP_status: 8 ChassisBus
    localDict = {'Not_Applied': 'Not Applied',
                 'Driver_applying_brakes': 'Applying'}
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)

    decodedBrakeStatus = translateResponse(
        localDict, decoded['ESP_driverBrakeApply'])
    if decodedBrakeStatus == "Applying":
        publish_mqtt(client, topic + "/custom_driver-brake",
                     "{}".format(decodedBrakeStatus) + ";#FF8300")  # Orange
    else:
        publish_mqtt(client, topic + "/custom_driver-brake",
                     "{}".format(decodedBrakeStatus) + ";#FFFF00")  # Yellow
    return


def DIspeed(client, msg):
    # BO_ 599 ID257DIspeed: 8 VehicleBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)
    # publish_mqtt(client, topic + "/cur_speed",
    #              "{:.1f}".format(decoded['DI_vehicleSpeed'] * .62))  # .62*kmph = mph
    decodedSpeed = decoded['DI_vehicleSpeed']*.62  # .62*kmph = mph
    if (decodedSpeed > 80):
        publish_mqtt(client, topic + "/custom_cur-speed",
                     "{:.1f}".format(decodedSpeed) + ";#FF8300")  # Orange
    else:
        publish_mqtt(client, topic + "/custom_cur-speed",
                     "{:.1f}".format(decodedSpeed) + ";#FFFF00")
    return


def SystemTimeUTC(client, msg):
    # BO_ 792 ID318SystemTimeUTC: 8 VehicleBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)
    publish_mqtt(client, topic + "/date_time", "{:02}\n{:} {:02}:{:02}:{:02}".format(
        decoded['UTCday318'], calendar.month_name[decoded['UTCmonth318']], decoded['UTChour318'], decoded['UTCminutes318'], decoded['UTCseconds318']))
    return


def DAS_statusclient(client, msg):
    # BO_ 921 ID399DAS_status: 8 ChassisBus
    localDict = {'LC_HANDS_ON_REQD_DETECTED': 'H_O Reqd', 'LC_HANDS_ON_REQD_NOT_DETECTED': 'H_O Req NotDet',
                 'UNAVAILABLE': 'Unavail', 'AVAILABLE': 'Avail', 6: 'Engaged'}
    global ApEngaged, ApDisengageCounter, ApInterveneCounter, DriverAcceleratorPressed, ApInterveneActive
    # print(msg)
    try:
        decoded = db.decode_message(msg.arbitration_id, msg.data)
        # print(decoded)

        decodedApState = translateResponse(
            localDict, decoded['DAS_autopilotState'])

        # AP HandState
        publish_mqtt(client, topic + "/ap-handstate",
                     "{}".format(translateResponse(localDict, decoded['DAS_autopilotHandsOnState'])))
        # AP Engaged no change
        if ((ApEngaged) and (decodedApState == "Engaged")):
            if ((DriverAcceleratorPressed == True) and (ApInterveneActive == False)):
                ApInterveneCounter += 1
                ApInterveneActive = True

            publish_mqtt(client, topic + "/custom_ap-state",
                         "{}".format(decodedApState) + ";#FFFFFF")  # white
        elif ((not ApEngaged) and (decodedApState == "Engaged")):
            # AP was just engaged set globabl True
            publish_mqtt(client, topic + "/custom_ap-state",
                         "{}".format(decodedApState) + ";#FFFFFF")  # white
            ApEngaged = True
        elif ((ApEngaged) and (decodedApState != "Engaged")):
            # AP Disengaged add to ApDisengageCounter
            ApDisengageCounter += 1
            ApEngaged = False
            publish_mqtt(client, topic + "/custom_ap-state",
                         "{}".format(decodedApState) + ";#FF8300")  # Yellow

        # Publish Disengage Count and Intervention Count
        publish_mqtt(client, topic + "/disengage-count",
                     "{}".format(ApDisengageCounter))
        publish_mqtt(client, topic + "/intervene-count",
                     "{}".format(ApInterveneCounter))
        return
    except Exception as ex:
        template = "DAS_Status exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        return


def Odometer(client, msg):
    # BO_ 950 ID3B6odometer: 4 VehicleBus
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded)
    publish_mqtt(client, topic + "/odometer",
                 "{:.1f}".format(decoded['Odometer3B6']))
    # publish_mqtt(client, topic + "/aptrip-odometer",
    #               "{:.1f}".format(ApTripLength))
    return


def translateResponse(myDict, canResponse):
    for key in myDict.keys():  # for name, age in dictionary.iteritems():  (for Python 2.x)
        if key == canResponse:
            return myDict[key]
    return ("Unkown_Response")


def getTimeDelayed(lastTimestamp, delayDesired):
    timeDiff = time.time() - lastTimestamp
    # print(timeDiff)
    if timeDiff > delayDesired:
        return True
    else:
        return False


def logMessage(logFilename, message, boolTimestamp):
    try:
        f = open(logFilename, "a")
        if boolTimestamp:
            f.write(
                "{0} -- {1}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M"), message))
        else:
            f.write("{0}\n".format(message))
        f.close()
    except Exception as ex:
        template = "Logger exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def run():
    client = connect_mqtt()
    client.loop_start()

    listenToCan(client)


if __name__ == '__main__':
    run()
