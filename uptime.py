# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from sensors.sensor import AbstractSensor

class UptimeSensor(AbstractSensor):
    def discover(self, target):
        return [{}]

    def check(self, checkinst):
        uptime, idle = (float(secs) for secs in open("/proc/uptime", "rb").read().strip().split())
        return {"uptime": uptime}, {}
