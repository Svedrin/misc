# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import re
import os
import json

from sensors.sensor import AbstractSensor

class EhzSensor(AbstractSensor):
    def discover(self, target):
        return []

    def check(self, checkinst):
        ret, out, err = self._invoke(["/root/libsml/examples/ehzpoll", checkinst["port"]])
        data = json.loads(out)
        return data, {}
