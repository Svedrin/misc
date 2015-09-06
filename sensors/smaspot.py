# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import re
import os
import subprocess

from sensors.sensor import AbstractSensor

class SmaSpotSensor(AbstractSensor):
    def discover(self, target):
        return []

    def check(self, checkinst):
        proc = subprocess.Popen(
                   ["/root/smaspot/SMAspot/bin/Release/SMAspot", "-v2", "-nocsv"],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
        out, err = proc.communicate()

        ret = {}

        wantlines = ("EToday", "ETotal", "Feed-In Time", "String", "Phase", "Total Pac")
        for line in out.split("\n"):
            line = line.strip()
            for wantline in wantlines:
                if line.startswith(wantline):
                    break
            else:
                continue

            values = re.findall(r'(?P<field>\w+)\s*:\s+(?P<value>\d+\.\d+)(?P<unit>\w*)', line)

            phase = re.findall(r'(String|Phase) (?P<phase>\d+)', line)
            if phase:
                phase = phase[0][1]
            else:
                phase = ''

            for field, valstr, unit in values:
                if unit.startswith("k"):
                    mult = 1000
                else:
                    mult = 1

                ret[field.lower() + phase] = float(valstr) * mult

        if not ret:
            ret = None

        return ret, {}
