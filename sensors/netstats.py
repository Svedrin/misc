# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from time import time, mktime
from datetime import datetime, timedelta

from pyudev import Context, Device, DeviceNotFoundByNameError

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class NetstatsSensor(AbstractSensor):
    def __init__(self, conf):
        AbstractSensor.__init__(self, conf)
        self._cache     = {}
        self._cachetime = {}

    def _get_via_ssh(self, target):
        try:
            import spur
        except ImportError:
            import logging
            logging.error("cannot import spur, SSH is not available")
            return {}

        # retrieve data via SSH by running grep to collect the info we need, then convert it into a dict such as:
        # {
        #   "uptime": 1337,
        #   "eth0":   { stats },
        #   "wlan0":  { stats }
        # }

        with spur.SshShell(hostname=target.name, username=target["ssh_username"], password=target["ssh_password"]) as sh:
            grepresult = sh.run(["sh", "-c", "grep . /proc/uptime /sys/class/net/*/statistics/* /sys/class/net/*/speed"], allow_error=True)

        result = {}

        for line in grepresult.output.split("\n"):
            line = line.strip()
            if not line:
                continue

            fpath, fcontent = line.split(":")

            if fpath == "/proc/uptime":
                result["uptime"] = float(fcontent.split()[0])

            elif "/statistics/" in fpath:
                _, _, _, _, iface, _, statkey = fpath.split("/")
                if iface not in result:
                    result[iface] = {}
                result[iface][statkey] = int(fcontent)

            elif "/speed" in fpath:
                _, _, _, _, iface, _ = fpath.split("/")
                if iface not in result:
                    result[iface] = {}
                result[iface]["speed"] = int(fcontent)

        return result

    def cache(self, target):
        if target.name not in self._cache or time() - self._cachetime[target.name] > 280:
            self._cache[target.name]     = self._get_via_ssh(target)
            self._cachetime[target.name] = time()
        return self._cache[target.name]

    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            if "ssh_username" not in target or "ssh_password" not in target:
                return []
            return [ {"interface": dev}
                for dev in self.cache(target)
                if dev != "uptime"
            ]
        ctx = Context()
        return [ {"interface": dev["INTERFACE"]}
            for dev in ctx.list_devices()
            if dev["SUBSYSTEM"] == "net"
        ]

    def can_activate(self, checkinst):
        if "ssh_username" in checkinst.target and "ssh_password" in checkinst.target:
            return checkinst["interface"] in self.cache(checkinst.target)

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

        # let's see if we need to do a remote check
        if checkinst.target.name != self.conf.environ["fqdn"]:
            data   = self.cache(checkinst.target)
            uptime = timedelta(seconds=data["uptime"])
            speed  = data[checkinst["interface"]].get("speed", None)
            if speed:
                speed *= 125000 # MBit/s -> bytes/s

            currstate = ValueDict(data[checkinst["interface"]])
            if "speed" in currstate:
                del currstate["speed"]

            currstate["timestamp"] = self._cachetime[checkinst.target.name]

        else:
            ctx = Context()
            dev = Device.from_name(ctx, "net", checkinst["interface"])

            if hasattr(dev, "time_since_initialized") and dev.time_since_initialized:
                uptime = dev.time_since_initialized
            else:
                with open( "/proc/uptime" ) as ut:
                    uptime = timedelta(seconds=float(ut.read().split()[0]))

            try:
                speed = int(dev.attributes["speed"]) * 125000 # MBit/s -> bytes/s
            except (KeyError, ValueError):
                speed = None

            statfields = os.listdir(dev.sys_path + "/statistics")

            currstate = ValueDict(zip(statfields, [
                int(dev.attributes["statistics/%s" % statfield]) for statfield in statfields
            ]))
            currstate["timestamp"] = time()

        createstamp = int(mktime((datetime.now() - uptime).timetuple()))

        if havestate and ("device" not in storedata or "initialized" not in storedata["device"] or createstamp != storedata["device"]["initialized"]):
            havestate = False

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
