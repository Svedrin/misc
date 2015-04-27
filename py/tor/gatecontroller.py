# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from time import sleep, time

class GateTimeout(Exception):
    pass

class GateController(object):
    PIN_MOTOR = 12
    PIN_UPPER = 18
    PIN_LOWER = 16

    def __init__(self, gpio, display, logger):
        self.gpio = gpio
        self.display = display
        self.logger = logger

        self.gpio.setmode(self.gpio.BOARD)
        self.gpio.setwarnings(False)

        self.gpio.setup(GateController.PIN_MOTOR, self.gpio.OUT)
        self.gpio.setup(GateController.PIN_UPPER, self.gpio.IN)
        self.gpio.setup(GateController.PIN_LOWER, self.gpio.IN)

    def trigger(self, direction_or_msg=None):
        """ Trigger the gate. """
        self.display.countdown(30, True)
        self.logger.debug("LET'S DO THIS")
        if direction_or_msg in ('up', 'down'):
            self.display.arrow(direction_or_msg, True)
        elif direction_or_msg:
            self.display.scrolltext(direction_or_msg)
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
                self.logger.info("Gate is transitioning. Waiting...")
                try:
                    self.wait_for_state("up", "down")
                except GateTimeout:
                    self.logger.debug("Gone in 30 seconds.")
                    self.trigger("Waiting")
                    continue
                else:
                    self.logger.debug("Waiting for state to settle...")
                    state = self.get_state()
                    self.display.arrow(state, move=False)
                    sleep(5)
                    state = self.get_state()

            self.logger.info("Gate is %s!" % state)

            if state != want:
                self.trigger(want)
                self.logger.debug("Waiting for gate to start moving...")
                self.wait_for_state("transitioning")
            else:
                break
