#!/usr/bin/env python3
########################################################################
# Filename    : UltrasonicRanging.py
# Description : Get distance via UltrasonicRanging sensor, qualify a rep
#				has started/finished, package up and POST data to API
# author      : www.freenove.com
# modification: 2019/12/28
# modified by : www.powerqueue.io
# modification: 2020/11/25
########################################################################
import RPi.GPIO as GPIO
import requests
import uuid
import json as jsn
import sys
import time
import datetime
from datetime import datetime, tzinfo, timedelta

trigPin = 40
echoPin = 38
MAX_DISTANCE = 220          # define the maximum measuring distance, unit: cm
timeOut = MAX_DISTANCE*60   # calculate timeout according to the maximum measuring distance
sensorSurfaceDistance = 90

class simple_utc(tzinfo):
    def tzname(self,**kwargs):
        return "UTC"
    def utcoffset(self, dt):
        return timedelta(hours=-6)

def pulseIn(pin,level,timeOut): # obtain pulse time of a pin under timeOut
    t0 = time.time()
    while(GPIO.input(pin) != level):
        if((time.time() - t0) > timeOut*0.000001):
            return 0;
    t0 = time.time()
    while(GPIO.input(pin) == level):
        if((time.time() - t0) > timeOut*0.000001):
            return 0;
    pulseTime = (time.time() - t0)*1000000
    return pulseTime

def getSonar():     # get the measurement results of ultrasonic module,with unit: cm
    GPIO.output(trigPin,GPIO.HIGH)      # make trigPin output 10us HIGH level
    time.sleep(0.00001)     # 10us
    GPIO.output(trigPin,GPIO.LOW) # make trigPin output LOW level
    pingTime = pulseIn(echoPin,GPIO.HIGH,timeOut)   # read plus time of echoPin
    distance = pingTime * 340.0 / 2.0 / 10000.0     # calculate distance with sound speed 340m/s
    return distance

def setup():
    GPIO.setmode(GPIO.BOARD)      # use PHYSICAL GPIO Numbering
    GPIO.setup(trigPin, GPIO.OUT)   # set trigPin to OUTPUT mode
    GPIO.setup(echoPin, GPIO.IN)    # set echoPin to INPUT mode

def motionDict(): 
    reqDict = {"SensorID": "",
      "LocationID": "",
        "MotionStartDt": "",
        "MotionEndDt": "",
        "Measurements": []}
    
    return reqDict

def measurementDict(newPosition):
    measurementObj = {"Measurements": [{
            "Report": str(sensorSurfaceDistance - newPosition),
            "ReportDT": datetime.utcnow().replace(tzinfo=simple_utc()).isoformat()
        }]}

def loop():
    while(True):
        distance = getSonar() # get distance
        print ("The distance is : %.2f cm"%(distance))
        #TO DO: measure the distance and if distance between sensor and surface decreseases by
        #25% begin adding all measurements to a KV of (distance, datetime.now) every millisecond
        #when distance is once again lower than decreased by 25% stop adding measurements to the KV
        #array and POST to admFitqueMotionAPI with location (self) for storage
        #FYI - no further intelligence required, analytics services will pair the data with whoever is
        #logged into the machine
        reqDict = motionDict()
        distanceRatio = distance/sensorSurfaceDistance
        print ("The distance ratio is : %.2f cm"%(distanceRatio))
        while distanceRatio <= 0.75:
            print ("Execise Rep has started with distance: %.2f"%(distance))
            repDistance = getSonar()
            print ("The repDistance is : %.2f cm"%(repDistance))

            if reqDict["Measurements"].__len__ == 0:
                reqDict["LocationID"] = "LA-Gunn_CableLatPull-1"
                reqDict["SensorID"] = "CABLELATPULL"
                reqDict["MotionStartDt"] = datetime.utcnow().replace(tzinfo=simple_utc()).isoformat()
                reqDict["MotionEndDt"] = datetime.utcnow().replace(tzinfo=simple_utc()).isoformat()
                
                reqDict["Measurements"].append(measurementDict(repDistance))
            else:
                reqDict["Measurements"].append(measurementDict(repDistance))

            time.sleep(.4)
            print ("The repDistance is : %.2f cm"%(repDistance))
            distance = repDistance
 
        if reqDict["Measurements"].__len__ >= 0:
                reqDict["MotionEndDt"] = datetime.utcnow().replace(tzinfo=simple_utc()).isoformat()
                #Send reqDict in POST
                headers = {'Content-Type': 'application/json'}
                url = 'http://192.168.1.178:3001/fitqueue-motion-api/v1/create-motion'
                print("Exercise Rep has ended.")
                print(jsn.dumps(reqDict))
                response = requests.request("POST", url, headers=headers, data=jsn.dumps(reqDict))
                print("Status code: ", response.status_code)
                print("Printing Entire Post Request")
                print(response.content)
                ######################

        time.sleep(1)

if __name__ == '__main__':     # Program entrance
    print ('Program is starting...')
    setup()
    try:
        loop()
    except KeyboardInterrupt:  # Press ctrl-c to end the program.
        GPIO.cleanup()         # release GPIO resource




