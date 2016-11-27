#!/usr/bin/env python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

# CAN bus exploration.

import threading

from datetime import datetime
from Queue import Queue
from time import sleep

class Bus(object):
    def __init__(self):
        self.clock    = False
        self.data     = True
        self.shutdown = False


bus = Bus()



def go(func, *args, **kwargs):
    thr = threading.Thread(target=func, args=args, kwargs=kwargs)
    thr.daemon = True
    thr.start()
    return thr


def go_nodaemon(func, *args, **kwargs):
    thr = threading.Thread(target=func, args=args, kwargs=kwargs)
    thr.daemon = False
    thr.start()
    return thr


outq    = Queue()
@go
def printer():
    while True:
        msg = outq.get()
        print "[%s] %s" % (datetime.now(), msg)


@go_nodaemon
def clock():
    while not bus.shutdown:
        outq.put("Tick")
        bus.clock = not bus.clock
        bus.data  = True
        sleep(1)


@go_nodaemon
def cpu1():
    lastclock = bus.clock
    current_tick = 0

    send_queue = [
        (    3,    "hallo" ),
        (   17,    "huhu"  ),
        (   25,    "jaho" ),
        (    3,    "hallo" ),
        ]
    message    = send_queue[0]
    sending_id = True
    id_pos     = 0
    body_pos   = 0
    start_at_tick = None

    while not bus.shutdown:
        if bus.clock and not lastclock:    # _/¯
            outq.put("cpu1: Tick %d" % current_tick)
            current_tick += 1

            # decide to start sending.
            if message is not None and start_at_tick is None:
                outq.put("cpu1 starting to send")
                start_at_tick = current_tick
                sending_id = True

            if start_at_tick is not None:
                # send one bit of ID if the bus is clear, then sleep and check again
                current_bit_idx = 11 - (current_tick - start_at_tick)
                if current_bit_idx >= 0:
                    my_bit = bool(message[0] & (1<<current_bit_idx))
                    if bus.data and not my_bit:    # high means clear in the ID phase
                        bus.data = my_bit          # ram it in the ground
                    outq.put("cpu1 sent a %s" % my_bit)
                    sleep(0.5)                     # give everyone a chance to overwrite me
                    if bus.data != my_bit:         # someone else killed our bit
                        outq.put("cpu1 is a sad panda and waits for the next frame.")
                else:
                    sending_id = False         # ID is complete
                    outq.put("cpu1 has completed sending ID %d" % message[0])

        lastclock = bus.clock
        sleep(0.1)


@go_nodaemon
def cpu2():
    lastclock = bus.clock
    current_tick = 0

    start_at_tick = None
    revd_id = 0

    while not bus.shutdown:
        if bus.clock and not lastclock:    # _/¯
            outq.put("cpu2: Tick %d" % current_tick)
            current_tick += 1

            # We don't have anything to send, so just read

            if start_at_tick is None:
                outq.put("cpu2 starting to read")
                start_at_tick = current_tick

            if start_at_tick is not None:
                sleep(0.5)

                current_bit_idx = 11 - (current_tick - start_at_tick)
                if current_bit_idx >= 0:
                    revd_id |= (bus.data<<current_bit_idx)
                    outq.put("cpu2 received a %s" % bus.data)
                else:
                    outq.put("cpu2 has completed receiving ID %s" % revd_id)

        lastclock = bus.clock
        sleep(0.1)



try:
    while True:
        sleep(99999)
except KeyboardInterrupt:
    outq.put("The machine has initiated its shutdown sequence. Please stand by.")
    bus.shutdown = True
