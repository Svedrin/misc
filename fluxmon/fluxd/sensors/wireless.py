# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from time import time

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class WirelessSensor(AbstractSensor):
    def _read_proc(self):
        fields = ["iface", "status", "qual_link", "qual_level", "qual_noise", "disc_nwid",
                  "disc_crypt", "disc_frag", "disc_retry", "disc_misc", "missed_beacon"]
        return [ dict(zip(fields, line.strip().replace(":", "").split())) for line in open("/proc/net/wireless", "rb").read().split("\n")[2:] if line ]

    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            return []
        return [ {"interface": iface["iface"]} for iface in self._read_proc() ]

    def check(self, checkinst):
        for iface in self._read_proc():
            if iface["iface"] == checkinst["interface"]:
                # Read the state file (if possible).
                storetime, storedata = self._load_store(checkinst["uuid"])
                havestate = (storedata is not None)

                absstats = ValueDict({
                    "qual_link":  float(iface["qual_link"]),
                    "qual_level": float(iface["qual_level"]),
                    "qual_noise": float(iface["qual_noise"]),
                    })

                relstats = ValueDict({
                    "disc_nwid":  float(iface["disc_nwid"]),
                    "disc_crypt": float(iface["disc_crypt"]),
                    "disc_frag":  float(iface["disc_frag"]),
                    "disc_retry": float(iface["disc_retry"]),
                    "disc_misc":  float(iface["disc_misc"]),
                    "missed_beacon": float(iface["missed_beacon"]),
                    "timestamp":  time()
                    })

                if havestate:
                    reldiff = relstats - storedata["relstats"]
                    reldiff /= reldiff["timestamp"]
                    del reldiff["timestamp"]
                    merged = {}
                    merged.update(absstats)
                    merged.update(reldiff)
                else:
                    merged = None

                self._save_store(checkinst["uuid"], {
                    "relstats": relstats,
                })

                return merged, {}
        return None, {}
