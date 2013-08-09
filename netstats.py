# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
from time import time

from pyudev import Context, Device

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class NetstatsSensor(AbstractSensor):
    def discover(self):
        ctx = Context()
        return [ dev["INTERFACE"]
            for dev in ctx.list_devices()
            if dev["SUBSYSTEM"] == "net"
        ]

    def check(self, iface):
        # Read the state file (if possible).
        storetime, storedata = self._load_store()

        ctx = Context()
        dev = Device.from_name(ctx, "net", iface)

        try:
            speed = int(dev.attributes["speed"]) * 125000
        except (KeyError, ValueError):
            speed = None

        statfields = os.listdir(dev.sys_path + "/statistics")

        currstate = ValueDict(zip(statfields, [
            int(dev.attributes["statistics/%s" % statfield]) for statfield in statfields
        ]))
        currstate["timestamp"] = time()

        if storedata is not None:
            diff = currstate - storedata["state"]
            diff /= diff["timestamp"]
            del diff["timestamp"]
        else:
            diff = None

        self._save_store({
            "state": currstate
        })

        return diff, {
            "rx_bytes": speed,
            "tx_bytes": speed
        }
