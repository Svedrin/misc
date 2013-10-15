# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import subprocess
import json

class SensorMeta(type):
    """ Meta class that keeps track of known check types. """
    sensortypes = {}

    def __init__( cls, name, bases, attrs ):
        type.__init__( cls, name, bases, attrs )
        if name.endswith("Sensor") and not name.startswith("Abstract"):
            sensortype = name.replace("Sensor", "").lower()
            SensorMeta.sensortypes[sensortype] = cls

class AbstractSensor(object):
    __metaclass__ = SensorMeta

    def __init__(self, conf):
        self.conf = conf

    def _invoke(self, args):
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        return proc.returncode, out, err

    def _load_store(self, uuid):
        fpath = os.path.join(self.conf.environ["datadir"], "%s.store.json" % uuid)
        if not os.path.exists(fpath):
            return None, None
        mtime = os.path.getmtime(fpath)
        fd = open(fpath, "rb")
        try:
            return mtime, json.load(fd)
        finally:
            fd.close()

    def _save_store(self, uuid, data):
        fpath = os.path.join(self.conf.environ["datadir"], "%s.store.json" % uuid)
        fd = open(fpath + ".new", "wb")
        try:
            json.dump(data, fd, indent=2)
        finally:
            fd.close()
        os.rename(fpath + ".new", fpath)

    def discover(self, target):
        raise NotImplementedError("discover() is abstract")

    def check(self, something):
        raise NotImplementedError("check() is abstract")
