# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from wolfobject import WolfObject
from sensors.sensor import SensorMeta

class Sensor(WolfObject):
    objtype = "sensor"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)

    @property
    def sensor(self):
        SensorType = SensorMeta.sensortypes[self.name]
        return SensorType(self._conf)

    def discover(self):
        return self.sensor.discover()

    def check(self, checkinst):
        return self.sensor.check(checkinst)
