# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import socket
import json

from time import time, mktime
from datetime import datetime, timedelta
from select import select

from pyudev import Context, Device, DeviceNotFoundByNameError

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class MeshpingSensor(AbstractSensor):
    def __init__(self, conf):
        AbstractSensor.__init__(self, conf)
        self.ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP)

        self._cache = None
        self._cachetime = 0
        self._cachereset = False

    def _cmd(self, command, **kwargs):
        self.ctrl.sendto(json.dumps(dict(kwargs, cmd=command)), ("127.0.0.1", 55432))
        rdy_read, _, _ = select([self.ctrl], [], [], 0.5)
        if self.ctrl in rdy_read:
            reply, addr = self.ctrl.recvfrom(2**14)
            return json.loads(reply)
        return None

    def cache(self, reset=False):
        if time() - self._cachetime > 280 or (reset and not self._cachereset):
            self._cache = self._cmd("list", reset=reset)
            self._cachetime = time()
            self._cachereset = reset
        return self._cache

    def discover(self, target):
        # if meshping knows target.name or we added it:
        #     return [{}]
        # else:
        #     return []
        for targetinfo in self.cache(reset=False).values():
            if targetinfo["name"] == target.name:
                return [{}]
        # self._cmd("add", name="yolo.example.not", addr="123.123.123.123") ?
        return []

    def can_activate(self, checkinst):
        # unless this host sucks for some reason,
        return True

    def check(self, checkinst):
        for targetinfo in self.cache(reset=True).values():
            if targetinfo["name"] == checkinst.target.name:
                avg = 0
                if targetinfo["recv"]:
                    avg = targetinfo["sum"] / targetinfo["recv"] * 1000
                return {
                    "sent": targetinfo["sent"],
                    "recv": targetinfo["recv"],
                    "errs": 0,
                    "avg":  avg,
                }, {}
        raise ValueError("target not found in data")
