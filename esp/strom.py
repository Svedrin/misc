import time
import usocket as socket
import mymqtt

from machine import Pin


def main(pin=4):
    cl = mymqtt.MQTTClient()
    cl.connect()

    state = dict(last_tick=0, last_check=0)

    def callback(p):
        this_tick = time.ticks_ms()

        # debounce: only accept if more than 100ms ago
        if this_tick > state["last_tick"] + 100:
            state["last_tick"] = this_tick

            if not state["last_check"]:
                print("Got first tick, waiting")

            else:
                state["delta"] = (state["last_tick"] - state["last_check"]) / 1000.
                state["watts"] = 1.0 / state["delta"] * 3600.
                print("Last tick at %(last_tick)d -- last check at %(last_check)d -- delta is %(delta).2f seconds -- consumption is %(watts).2f Watts" % state)
                cl.publish("strom/%(name)s/delta", state["delta"])
                cl.publish("strom/%(name)s/watts", state["watts"])

            state["last_check"] = state["last_tick"]


    p4 = Pin(pin, Pin.IN)
    p4.irq(trigger=Pin.IRQ_RISING, handler=callback)
