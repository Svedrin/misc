# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from sensors.sensor import AbstractSensor

class CoreTempSensor(AbstractSensor):
    def discover(self):
        return [ "%s/%s" % ( name.split('.', 1)[1], field.split('_')[0][4:] )
            for name in os.listdir('/sys/devices/platform')
            if name.startswith("coretemp.")
            for field in os.listdir(os.path.join('/sys/devices/platform', name))
            if field.startswith("temp") and field.endswith("_input")]

    def check(self, uuid, target):
        coretemp, tempidx = target.split('/')
        return {
            "temp": int(open("/sys/devices/platform/coretemp.%s/temp%s_input" % (coretemp, tempidx), "rb").read().strip()) / 1000.
        }, {
            "temp": int(open("/sys/devices/platform/coretemp.%s/temp%s_crit"  % (coretemp, tempidx), "rb").read().strip()) / 1000.
        }
