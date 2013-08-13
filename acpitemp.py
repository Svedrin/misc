# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from pyudev import Context, Device

from sensors.sensor import AbstractSensor

class AcpiTempSensor(AbstractSensor):
    def discover(self):
        return [name.replace("thermal_zone", "") for name in os.listdir('/sys/devices/virtual/thermal') if name.startswith("thermal_zone")]

    def check(self, uuid, tzone):
        ctx = Context()
        dev = Device.from_sys_path(ctx, "/sys/devices/virtual/thermal/thermal_zone" + tzone)
        crittemp = None
        for key in dev.attributes:
            if key.startswith("trip_point_") and key.endswith("_type") and dev.attributes[key] == "critical":
                crittemp = int(dev.attributes[key.replace("_type", "_temp")]) / 1000.
        return {
            "temp": int(dev.attributes["temp"]) / 1000.
        }, {
            "temp": crittemp
        }
