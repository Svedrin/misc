# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import signal
import random

class BaseGPIO(object):
    BOARD = None
    HIGH  = True
    LOW   = False
    IN    = True
    OUT   = False

    def setwarnings(self, mode):
        pass

    def setmode(self, mode):
        pass

    def setup(self, pin, mode):
        pass

    def input(self, pin):
        return False

    def output(self, pin, value):
        print "Setting pin %d to %s" % (pin, value)


class Gate(BaseGPIO):
    def __init__(self):
        self.state = random.choice(["down", "up", "unknown"])
        print u"→ state initialized as", self.state

    def input(self, pin):
        if pin == 18: # upper pin needs to be false if gate is up
            return not self.state == "up"
        if pin == 16: # lower pin needs to be false if gate is down
            return not self.state == "down"

    def output(self, pin, value):
        if not value:
            return
        if random.randint(0, 4) == 0:
            signal.signal(signal.SIGALRM, self.state_unknown)
            signal.alarm(5)
        else:
            if self.state == "up":
                signal.signal(signal.SIGALRM, self.state_down)
            else:
                signal.signal(signal.SIGALRM, self.state_up)
            signal.alarm(25)
        self.state = "transitioning"

    def state_up(self, *args):
        print u"→ setting state to up".encode("utf-8")
        self.state = "up"

    def state_down(self, *args):
        print u"→ setting state to down".encode("utf-8")
        self.state = "down"

    def state_unknown(self, *args):
        print u"→ setting state to unknown".encode("utf-8")
        self.state = "unknown"


GPIO = Gate()
