# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from sensors.sensor import AbstractSensor

class LinuxLoadSensor(AbstractSensor):
    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            return []

        return [{}]

    def check(self, checkinst):
        return dict(zip(("load1", "load5", "load15"), (float(secs) for secs in open("/proc/loadavg").read().strip().split()[:3]))), {}
