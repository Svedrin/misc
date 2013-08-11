# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
from time import time, mktime
from datetime import datetime, timedelta

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

    def check(self, uuid, iface):
        # Read the state file (if possible).
        storetime, storedata = self._load_store(uuid)
        havestate = (storedata is not None)

        ctx = Context()
        dev = Device.from_name(ctx, "net", iface)

        if hasattr(dev, "time_since_initialized") and dev.time_since_initialized:
            uptime = dev.time_since_initialized
        else:
            with open( "/proc/uptime" ) as ut:
                uptime = timedelta(seconds=int(float(ut.read().split()[0])))

        createstamp = int(mktime((datetime.now() - uptime).timetuple()))

        if havestate and ("device" not in storedata or "initialized" not in storedata["device"] or createstamp != storedata["device"]["initialized"]):
            havestate = False

        try:
            speed = int(dev.attributes["speed"]) * 125000
        except (KeyError, ValueError):
            speed = None

        statfields = os.listdir(dev.sys_path + "/statistics")

        currstate = ValueDict(zip(statfields, [
            int(dev.attributes["statistics/%s" % statfield]) for statfield in statfields
        ]))
        currstate["timestamp"] = time()

        if havestate:
            diff = currstate - storedata["state"]
            diff /= diff["timestamp"]
            del diff["timestamp"]
        else:
            diff = None

        self._save_store(uuid, {
            "state": currstate,
            "device": {
                "initialized": createstamp
            },
        })

        return diff, {
            "rx_bytes": speed,
            "tx_bytes": speed
        }
