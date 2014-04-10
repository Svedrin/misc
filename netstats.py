# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
from time import time, mktime
from datetime import datetime, timedelta

from pyudev import Context, Device, DeviceNotFoundByNameError

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class NetstatsSensor(AbstractSensor):
    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            return []
        ctx = Context()
        return [ {"interface": dev["INTERFACE"]}
            for dev in ctx.list_devices()
            if dev["SUBSYSTEM"] == "net"
        ]

    def can_activate(self, checkinst):
        try:
            ctx = Context()
            dev = Device.from_name(ctx, "net", checkinst["interface"])
        except DeviceNotFoundByNameError:
            return False
        return True

    def check(self, checkinst):
        # Read the state file (if possible).
        storetime, storedata = self._load_store(checkinst["uuid"])
        havestate = (storedata is not None)

        ctx = Context()
        dev = Device.from_name(ctx, "net", checkinst["interface"])

        if hasattr(dev, "time_since_initialized") and dev.time_since_initialized:
            uptime = dev.time_since_initialized
        else:
            with open( "/proc/uptime" ) as ut:
                uptime = timedelta(seconds=float(ut.read().split()[0]))

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

        self._save_store(checkinst["uuid"], {
            "state": currstate,
            "device": {
                "initialized": createstamp
            },
        })

        return diff, {
            "rx_bytes": speed,
            "tx_bytes": speed
        }
