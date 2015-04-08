# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import unittest

from rpi_mock import DeterministicGate
from tor import GateController

def log_print(message):
    pass

class TestDeterministicGate(unittest.TestCase):
    """ Test that DeterministicGate returns the correct status flags and counts triggers correctly. """

    def test_get_state_down(self):
        gpio = DeterministicGate("down")
        self.assertFalse(gpio.input(GateController.PIN_LOWER))
        self.assertTrue(gpio.input(GateController.PIN_UPPER))

    def test_get_state_up(self):
        gpio = DeterministicGate("up")
        self.assertTrue(gpio.input(GateController.PIN_LOWER))
        self.assertFalse(gpio.input(GateController.PIN_UPPER))

    def test_get_state_transitioning(self):
        gpio = DeterministicGate("unknown")
        self.assertTrue(gpio.input(GateController.PIN_LOWER))
        self.assertTrue(gpio.input(GateController.PIN_UPPER))

    def test_get_state_broken(self):
        gpio = DeterministicGate("broken")
        self.assertFalse(gpio.input(GateController.PIN_LOWER))
        self.assertFalse(gpio.input(GateController.PIN_UPPER))

    def test_trigger(self):
        gpio = DeterministicGate("unknown")

        # Test normal triggering -- init...
        self.assertEqual(gpio.motor_pin_state, False)
        self.assertEqual(gpio.triggered, 0)

        # Test normal triggering -- trigger once...
        gpio.output(GateController.PIN_MOTOR, True)
        self.assertEqual(gpio.motor_pin_state, True)
        self.assertEqual(gpio.triggered, 0)
        gpio.output(GateController.PIN_MOTOR, False)
        self.assertEqual(gpio.motor_pin_state, False)
        self.assertEqual(gpio.triggered, 1)
        self.assertEqual(gpio.state, "unknown")

        # Test normal triggering -- trigger twice, with a new state...
        gpio.states_after_trigger.append((0, "up"))
        gpio.output(GateController.PIN_MOTOR, True)
        self.assertEqual(gpio.motor_pin_state, True)
        self.assertEqual(gpio.triggered, 1)
        gpio.output(GateController.PIN_MOTOR, False)
        self.assertEqual(gpio.motor_pin_state, False)
        self.assertEqual(gpio.triggered, 2)
        self.assertEqual(gpio.state, "up")

        # Try to output something on the input ports
        with self.assertRaises(KeyError):
            gpio.output(GateController.PIN_LOWER, True)
        with self.assertRaises(KeyError):
            gpio.output(GateController.PIN_UPPER, True)

        # Try switching off the motor port while it's off already
        with self.assertRaises(ValueError):
            gpio.output(GateController.PIN_MOTOR, False)

        # Try switching on the motor port while it's on already
        gpio.output(GateController.PIN_MOTOR, True)
        with self.assertRaises(ValueError):
            gpio.output(GateController.PIN_MOTOR, True)


class TestGateControllerBasics(unittest.TestCase):
    """ Test that GateController deduces the correct states from the pin states and triggering works correctly. """
    def test_get_state_down(self):
        gpio = DeterministicGate("down")
        ctrl = GateController(gpio, log_print)
        self.assertEqual(ctrl.get_state(), "down")

    def test_get_state_up(self):
        gpio = DeterministicGate("up")
        ctrl = GateController(gpio, log_print)
        self.assertEqual(ctrl.get_state(), "up")

    def test_get_state_transitioning(self):
        gpio = DeterministicGate("unknown")
        ctrl = GateController(gpio, log_print)
        self.assertEqual(ctrl.get_state(), "transitioning")

    def test_get_state_broken(self):
        gpio = DeterministicGate("broken")
        ctrl = GateController(gpio, log_print)
        with self.assertRaises(ValueError):
            ctrl.get_state()

    def test_trigger(self):
        gpio = DeterministicGate("unknown")
        ctrl = GateController(gpio, log_print)
        self.assertFalse(gpio.motor_pin_state)
        self.assertEqual(gpio.triggered, 0)
        ctrl.trigger()
        self.assertFalse(gpio.motor_pin_state)
        self.assertEqual(gpio.triggered, 1)
        ctrl.trigger()
        self.assertFalse(gpio.motor_pin_state)
        self.assertEqual(gpio.triggered, 2)



if __name__ == '__main__':
    unittest.main()

