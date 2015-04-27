#!/usr/bin/env python
# kate: space-indent on; indent-width 4; replace-tabs on;

from ConfigParser import ConfigParser

import sys
import os
import os.path
import requests
import logging

from gatecontroller import GateController
from displaycontroller import DisplayController

class PushoverHandler(logging.Handler):
    """ A logging handler that sends messages via pushover.net.

        Inspired by <https://github.com/zacharytamas/django-pushover>.
    """
    def __init__(self, level, conf):
        logging.Handler.__init__(self, level)
        self.conf = conf

    def emit(self, record):
        try:
            requests.post( self.conf.get("pushover", "url"), {
                "token":   self.conf.get("pushover", "token"),
                "user":    self.conf.get("pushover", "user"),
                "message": record.getMessage()
            })
        except Exception:
            import traceback
            traceback.print_exc()


def main():
    unbufed = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stdout = unbufed

    logger = logging.getLogger('GateController')
    logger.setLevel(logging.DEBUG)
    if sys.stdout.isatty():
        logger.addHandler(logging.StreamHandler(sys.stdout))
    else:
        logger.addHandler(logging.FileHandler("/tmp/gate.log"))

    conf = ConfigParser()
    conf.add_section("pushover")
    conf.set("pushover", "enabled", "no")
    if conf.read(os.environ["HOME"] + "/.gate-pushover.ini") and conf.getboolean("pushover", "enabled"):
        logger.addHandler( PushoverHandler(logging.INFO, conf) )

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
        logging.warn("RPi module is not available, mocking it. Nothing is going to happen in the real world(tm).")
        from rpi_mock import RandomGate
        randomlogger = logging.getLogger("RandomGate")
        randomlogger.setLevel(logging.DEBUG)
        GPIO = RandomGate(randomlogger)

    if os.path.exists("/dev/ttyUSB0"):
        display = DisplayController("/dev/ttyUSB0", 9600, logger)
    elif os.path.exists("/dev/ttyAMA0"):
        display = DisplayController("/dev/ttyAMA0", 9600, logger)
    else:
        raise SystemError("display not found at /dev/ttyUSB0 or /dev/ttyAMA0")

    display.off()

    gate = GateController(GPIO, display, logger)
    if want is None:
        logger.info("Gate is %s!", gate.get_state())
    elif want == "trigger":
        gate.trigger()
    else:
        gate.move_to_state(want)

    display.off()


if __name__ == '__main__':
    main()
