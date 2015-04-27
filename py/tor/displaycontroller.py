# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import serial
from time import sleep, time

class DisplayError(Exception):
    pass

class DisplayController(object):
    def __init__(self, port, baud, logger):
        self.logger = logger
        self.ser = serial.Serial(port, baud)
        self.ser.setTimeout(1.5)
        self.countdown_running = False

    def command(self, command):
        self.logger.debug("sending %s to display", command)
        self.ser.write(command + "\n")
        answer = self.ser.readline().strip()
        self.logger.debug("got %s from display", answer)
        if answer == "FAIL":
            raise DisplayError(command)

    def off(self):
        self.command("off")

    def scrolltext(self, text):
        self.command("scrolltext %s" % text)

    def fill(self, direction, lines):
        if direction not in ('top', 'btm', 'lft', 'rgt'):
            raise ValueError("direction %s not in ('top', 'btm', 'lft', 'rgt')" % direction)
        self.command("fill%s %d" % (direction, lines))

    def countdown(self, seconds, wait=False):
        if seconds < 1 or seconds > 99:
            raise ValueError("seconds must be between 1 and 100")
        self.command("countdown %d" % seconds)
        self.countdown_running = True
        if wait:
            self.wait_for_countdown()

    def wait_for_countdown(self):
        if not self.countdown_running:
            return
        while self.ser.readline().strip() != "t=0":
            sleep(0.9)

    def arrow(self, direction, move=False):
        if direction not in ('up', 'down'):
            raise ValueError("direction %s not in ('up', 'down')" % direction)
        self.command("arrow%s%s" % ("move" if move else "", direction))

    def blocked(self):
        self.command("blocked")
