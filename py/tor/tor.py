#!/usr/bin/env python
# kate: space-indent on; indent-width 4; replace-tabs on;

from ConfigParser import ConfigParser
from time import sleep, time

import sys
import os
import requests

class GateTimeout(Exception):
    pass

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
        """ Trigger the gate. """
        self.log("LET'S DO THIS")
        self.gpio.output(GateController.PIN_MOTOR, self.gpio.HIGH)
        sleep(0.2)
        self.gpio.output(GateController.PIN_MOTOR, self.gpio.LOW)

    def get_state(self):
        """ Get the current gate status. """
        upper = not self.gpio.input(GateController.PIN_UPPER)
        lower = not self.gpio.input(GateController.PIN_LOWER)
        if upper and lower:
            raise ValueError("The gate appears to be both up and down.")
        if upper:
            return "up"
        if lower:
            return "down"
        return "transitioning"

    def wait_for_state(self, *states, **kwargs):
        """ wait_for_state('up', 'down', timeout=30, interval=1)

            Wait for the gate to reach one of the given states. If the timeout is reached,
            GateTimeout is raised.
        """
        if not states:
            raise ValueError("need at least one state to wait for")
        timeout  = kwargs.get("timeout",  30)
        interval = kwargs.get("interval",  1)
        start = time()
        while self.get_state() not in states:
            if time() - start >= timeout:
                raise GateTimeout()
            sleep(interval)

    def move_to_state(self, want):
        """ Move the gate by triggering it repeatedly until it reaches the state we want. """
        while True:
            state = self.get_state()

            if state == "transitioning":
                self.log("Gate is transitioning. Waiting...")
                try:
                    self.wait_for_state("up", "down")
                except GateTimeout:
                    self.log("Gone in 30 seconds.")
                    self.trigger()
                    continue
                else:
                    print "Waiting for state to settle..."
                    sleep(5)
                    state = self.get_state()

            self.log("Gate is %s!" % state)

            if state != want:
                self.trigger()
                print "Waiting for gate to start moving..."
                self.wait_for_state("transitioning")
            else:
                break


if __name__ == '__main__':
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

    if len(sys.argv) > 1:
        want = sys.argv[-1]
        if want not in ("up", "down", "trigger"):
            print "Command can only be one of up, down and trigger."
            sys.exit(255)
    else:
        want = None

    try:
        from RPi import GPIO
    except ImportError:
        print "RPi module is not available, mocking it. Nothing is going to happen in the real world(tm)."
        from rpi_mock import GPIO

    gate = GateController(GPIO, log)
    if want is None:
        log("Gate is %s!" % gate.get_state())
    elif want == "trigger":
        gate.trigger()
    else:
        gate.move_to_state(want)
