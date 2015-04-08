#!/usr/bin/env python
# kate: space-indent on; indent-width 4; replace-tabs on;

from ConfigParser import ConfigParser

import sys
import os
import requests

from gatecontroller import GateController

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
        from rpi_mock import RandomGate
        GPIO = RandomGate()

    gate = GateController(GPIO, log)
    if want is None:
        log("Gate is %s!" % gate.get_state())
    elif want == "trigger":
        gate.trigger()
    else:
        gate.move_to_state(want)
