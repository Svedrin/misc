# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from sensors.sensor import AbstractSensor

class CoreTempSensor(AbstractSensor):
    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            return []
        return [ {"zone": name.split('.', 1)[1], "tsensor": field.split('_')[0][4:]}
            for name in os.listdir('/sys/devices/platform')
            if name.startswith("coretemp.")
            for field in os.listdir(os.path.join('/sys/devices/platform', name))
            if field.startswith("temp") and field.endswith("_input")]

    def check(self, checkinst):
        fmt = "/sys/devices/platform/coretemp.%(zone)s/temp%(tsensor)s_%(field)s"
        params = {
            'zone': checkinst["zone"],
            'tsensor': checkinst["tsensor"]
        }

        if not os.path.exists(fmt % dict(params, field="input")):
            fmt = "/sys/devices/platform/coretemp.%(zone)s/hwmon/hwmon1/temp%(tsensor)s_%(field)s"

        return {
            "temp": int(fmt % dict(params, field="input"), "rb").read().strip()) / 1000.
        }, {
            "temp": int(fmt % dict(params, field="crit" ), "rb").read().strip()) / 1000.
        }
