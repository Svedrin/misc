# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import logging

from uuid import uuid4
from time import time

from wolfobject  import WolfObject
from observer    import Dispatcher


class Check(WolfObject):
    objtype = "check"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)
        self.sensor = self.find_object(params["sensor"])
        self.target = self.find_object(self.params["target"].split(":")[0])
        self.node   = self.find_object(params["node"])
        self.node.checks.append(self)
        self.target.target_checks.append(self)
        self.event = Dispatcher()
        self.event["updated"] = False

        self.is_active = (params.get("is_active", "true") == "true")
        if self.is_active:
            self.activate()

    def activate(self):
        self.is_active = self.sensor.can_activate(self)

    def __call__(self):
        res = {
            "uuid":         str(uuid4()),
            "timestamp":    int(time()),
            "check":        self["uuid"],
            "data":         None,
            "max":          None,
            "errmessage":   None,
        }

        try:
            res["data"], res["max"] = self.sensor.check(self)
        except Exception, err:
            import traceback
            logging.error(traceback.format_exc())
            res["errmessage"] = unicode(type(err)) + ": " + unicode(err),
        else:
            if res["data"] is None:
                logging.warning("Sensor for %s didn't return any data..." % self["uuid"])

        return res

