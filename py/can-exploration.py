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
        (    3, "hallo".ljust(8, '-') ),
        (   17, "huhu".ljust(8, '-')  ),
        (   25, "jaho".ljust(8, '-')  ),
        (    3, "hallo".ljust(8, '-') ),
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
                    if my_bit and not bus.data:    # someone else killed our bit
                        outq.put("cpu1 is a sad panda and waits for the next frame.")
                else:
                    if sending_id:
                        sending_id = False         # ID is complete
                        outq.put("cpu1 has completed sending ID %d" % message[0])

                    if body_pos < 8 * 8:
                        # the message can be sent unconditionally
                        body_char_idx = body_pos // 8
                        body_bit_idx  = body_pos  % 8
                        body_pos += 1
                        if body_char_idx < 8:
                            bus.data = bool(ord(message[1][body_char_idx]) & (1<<body_bit_idx))
                            outq.put("cpu1 sent a %s" % bus.data)
                            sleep(0.5)
                            # recv part is empty
                        else:
                            message = None
                            start_at_tick = None
                            outq.put("cpu1 message complete")

        lastclock = bus.clock
        sleep(0.1)


@go_nodaemon
def cpu2():
    lastclock = bus.clock
    current_tick = 0

    start_at_tick = None
    revd_id = 0
    recving_id = True

    revd_message = ""
    recv_buf = 0
    recv_buf_pos = 0

    while not bus.shutdown:
        if bus.clock and not lastclock:    # _/¯
            outq.put("cpu2: Tick %d" % current_tick)
            current_tick += 1

            # We don't have anything to send, so just read

            if start_at_tick is None:
                outq.put("cpu2 starting to read")
                start_at_tick = current_tick

            if start_at_tick is not None:
                # send part is empty
                sleep(0.5)

                outq.put("cpu2 received a %s" % bus.data)

                current_bit_idx = 11 - (current_tick - start_at_tick)
                if current_bit_idx >= 0:
                    revd_id |= (bus.data<<current_bit_idx)
                else:
                    if recving_id:
                        recving_id = False
                        outq.put("cpu2 has completed receiving ID %s" % revd_id)

                    recv_buf |= (bus.data<<recv_buf_pos)
                    recv_buf_pos += 1

                    if recv_buf_pos == 8:
                        revd_message += chr(recv_buf)
                        recv_buf = 0
                        recv_buf_pos = 0

                        outq.put("cpu2 is receiving a message: %s" % revd_message)
                        if len(revd_message) == 8:
                            outq.put("cpu2 message is complete: %s" % revd_message)
                            revd_message = ""


        lastclock = bus.clock
        sleep(0.1)



try:
    while True:
        sleep(99999)
except KeyboardInterrupt:
    outq.put("The machine has initiated its shutdown sequence. Please stand by.")
    bus.shutdown = True
