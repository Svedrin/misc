#!/usr/bin/env python
# kate: space-indent on; indent-width 4; replace-tabs on;

from ConfigParser import ConfigParser
from time import sleep, time

import RPi.GPIO as GPIO
import sys
import os
import requests

unbufed = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = unbufed

conf = ConfigParser()
HAVE_PUSHOVER = bool(conf.read("pushover.ini"))

def log(message):
    print message
    if False and HAVE_PUSHOVER and not sys.stdout.isatty():
        try:
            requests.post( conf.get("pushover", "url"), {
                "token":   conf.get("pushover", "token"),
                "user":    conf.get("pushover", "user"),
                "message": message
            })
        except Exception, err:
            import traceback
            traceback.print_exc()

PIN_MOTOR = 12
PIN_UPPER = 18
PIN_LOWER = 16

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

GPIO.setup(PIN_MOTOR, GPIO.OUT)
GPIO.setup(PIN_UPPER, GPIO.IN)
GPIO.setup(PIN_LOWER, GPIO.IN)

def trigger():
    log("LET'S DO THIS")
    GPIO.output(PIN_MOTOR, GPIO.HIGH)
    sleep(0.2)
    GPIO.output(PIN_MOTOR, GPIO.LOW)

if len(sys.argv) > 1:
    want = sys.argv[-1]
    if want not in ("up", "down"):
        print "Target state can only be up or down"
        sys.exit(255)
else:
    want = None

start = time()
while True:
    upper = not GPIO.input(PIN_UPPER)
    lower = not GPIO.input(PIN_LOWER)

    if want is not None and not upper and not lower:
        log("Gate is transitioning. Waiting...")
        while not upper and not lower:
            if time() - start >= 60:
                print "Gone in 60 seconds."
                start = time()
                trigger()
            sleep(1)
            upper = not GPIO.input(PIN_UPPER)
            lower = not GPIO.input(PIN_LOWER)
        print "Waiting for state to settle..."
        sleep(5)

    if upper and lower:
        print "WTF"
        sys.exit(2)

    if upper:
        state = "up"
    elif lower:
        state = "down"
    else:
        state = "transitioning"

    log("Gate is %s!" % state)

    if want is not None and state != want:
        trigger()
        print "Waiting for gate to start moving..."
        while (state == "up"   and not GPIO.input(PIN_UPPER)) or \
              (state == "down" and not GPIO.input(PIN_LOWER)):
            sleep(1)
    else:
        break
