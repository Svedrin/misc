#!/usr/bin/env python
# kate: space-indent on; indent-width 4; replace-tabs on;

from ConfigParser import ConfigParser
from time import sleep, time

from RPi import GPIO

import sys
import os
import requests

unbufed = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = unbufed



class GateController(object):
    PIN_MOTOR = 12
    PIN_UPPER = 18
    PIN_LOWER = 16

    def __init__(self, gpio, log):
        self.gpio = gpio
        self.log  = log

        self.gpio.setmode(self.gpio.BOARD)
        self.gpio.setwarnings(False)

        self.gpio.setup(GateController.PIN_MOTOR, self.gpio.OUT)
        self.gpio.setup(GateController.PIN_UPPER, self.gpio.IN)
        self.gpio.setup(GateController.PIN_LOWER, self.gpio.IN)

    def trigger(self):
        self.log("LET'S DO THIS")
        self.gpio.output(GateController.PIN_MOTOR, self.gpio.HIGH)
        sleep(0.2)
        self.gpio.output(GateController.PIN_MOTOR, self.gpio.LOW)

    def move_to_state(self, want):
        start = time()
        while True:
            upper = not self.gpio.input(GateController.PIN_UPPER)
            lower = not self.gpio.input(GateController.PIN_LOWER)

            if want is not None and not upper and not lower:
                self.log("Gate is transitioning. Waiting...")
                while not upper and not lower:
                    if time() - start >= 60:
                        print "Gone in 60 seconds."
                        start = time()
                        self.trigger()
                    sleep(1)
                    upper = not self.gpio.input(GateController.PIN_UPPER)
                    lower = not self.gpio.input(GateController.PIN_LOWER)
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

            self.log("Gate is %s!" % state)

            if want is not None and state != want:
                self.trigger()
                print "Waiting for gate to start moving..."
                while (state == "up"   and not self.gpio.input(GateController.PIN_UPPER)) or \
                    (state == "down" and not self.gpio.input(GateController.PIN_LOWER)):
                    sleep(1)
            else:
                break


if __name__ == '__main__':
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

    if len(sys.argv) > 1:
        want = sys.argv[-1]
        if want not in ("up", "down"):
            print "Target state can only be up or down"
            sys.exit(255)
    else:
        want = None

    gate = GateController(GPIO, log)
    gate.move_to_state(want)

