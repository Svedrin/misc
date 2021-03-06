# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import signal
import random

from gatecontroller import GateController

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


class DeterministicGate(BaseGPIO):
    def __init__(self, state):
        self.state = state
        self.motor_pin_state = False
        self.triggered = 0
        self.states_after_trigger = []

    def input(self, pin):
        if pin == GateController.PIN_UPPER: # upper pin needs to be false if gate is up
            return self.state not in ("up",   "broken")
        if pin == GateController.PIN_LOWER: # lower pin needs to be false if gate is down
            return self.state not in ("down", "broken")

    def output(self, pin, value):
        if pin != GateController.PIN_MOTOR:
            raise KeyError("That pin is unused")
        if value:
            if not self.motor_pin_state:
                self.motor_pin_state = True
            else:
                raise ValueError("motor pin is already high")
        else:
            if self.motor_pin_state:
                self.motor_pin_state = False
                self.triggered += 1
                self.check_state_switch()
            else:
                raise ValueError("motor pin is already low")

    def check_state_switch(self):
        if self.states_after_trigger:
            if self.states_after_trigger[0] is None:
                self.states_after_trigger.pop(0)
            elif self.states_after_trigger[0][0] > 0:
                signal.signal(signal.SIGALRM, self.do_state_switch)
                signal.alarm(self.states_after_trigger[0][0])
            else:
                self.do_state_switch()

    def do_state_switch(self, *args):
        self.state = self.states_after_trigger.pop(0)[1]
        self.check_state_switch()

class RandomGate(BaseGPIO):
    def __init__(self, logger):
        self.logger = logger
        self.state = random.choice(["down", "up", "unknown"])
        self.logger.debug(u"→ state initialized as %s", self.state)

    def input(self, pin):
        if pin == GateController.PIN_UPPER: # upper pin needs to be false if gate is up
            return not self.state == "up"
        if pin == GateController.PIN_LOWER: # lower pin needs to be false if gate is down
            return not self.state == "down"

    def output(self, pin, value):
        if not value:
            return
        watdo = random.randint(0, 10)
        if watdo == 0:
            signal.signal(signal.SIGALRM, self.state_unknown)
        elif watdo <= 5:
            signal.signal(signal.SIGALRM, self.state_up)
        else:
            signal.signal(signal.SIGALRM, self.state_down)
        signal.alarm(random.randint(20, 35))
        self.state = "transitioning"

    def state_up(self, *args):
        self.logger.debug(u"→ setting state to up")
        self.state = "up"

    def state_down(self, *args):
        self.logger.debug(u"→ setting state to down")
        self.state = "down"

    def state_unknown(self, *args):
        self.logger.debug(u"→ setting state to unknown")
        self.state = "unknown"
