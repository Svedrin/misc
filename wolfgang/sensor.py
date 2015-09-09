# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from wolfobject import WolfObject
from sensors.sensor import SensorMeta

class Sensor(WolfObject):
    objtype = "sensor"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)
        self._sensor = None

    @property
    def sensor(self):
        if self._sensor is None:
            SensorType = SensorMeta.sensortypes[self.name]
            self._sensor = SensorType(self._conf)
        return self._sensor

    def can_activate(self, checkinst):
        return self.sensor.can_activate(checkinst)

    def discover(self, target):
        return self.sensor.discover(target)

    def check(self, checkinst):
        return self.sensor.check(checkinst)
