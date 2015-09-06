# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

import os

from time import time

from NetApp import NaServer

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class NaVolumePerfSensor(AbstractSensor):
    def __init__(self, conf):
        AbstractSensor.__init__(self, conf)
        self.cache = {}

    def connect(self, hostname, username, password):
        serv = NaServer.NaServer(hostname, 1, 1)
        serv.set_server_type("Filer")
        serv.set_admin_user(username, password)
        serv.set_transport_type("HTTPS")
        return serv

    def discover(self, target):
        if target.name == self.conf.environ["fqdn"]:
            return []
        serv = self.connect(target.name, target["netapp_username"], target["netapp_password"])
        elem = NaServer.NaElement('volume-list-info')
        ret = serv.invoke_elem(elem)
        return [ {"volume": vol.child_get_string("name")}
            for vol in ret.element["children"][0].element["children"]
            ]

    def check(self, checkinst):
        if checkinst.target.name in self.cache:
            age, ret = self.cache[checkinst.target.name]
            if time() - age > 280:
                age, ret = None, None
                del self.cache[checkinst.target.name]
        else:
            age, ret = None, None

        if ret is None:
            serv = self.connect(checkinst.target.name, checkinst.target["netapp_username"], checkinst.target["netapp_password"])
            elem = NaServer.NaElement('perf-object-get-instances-iter-start')
            elem.child_add(NaServer.NaElement('objectname', 'volume'))
            tag_ret = serv.invoke_elem(elem)
            tag = tag_ret.child_get_string("tag")

            elem = NaServer.NaElement('perf-object-get-instances-iter-next')
            elem.child_add(NaServer.NaElement('tag', tag))
            elem.child_add(NaServer.NaElement('maximum', 99999))
            ret = serv.invoke_elem(elem)

        if age is None:
            age = time()
            self.cache[checkinst.target.name] = (age, ret)

        for volelement in ret.child_get("instances").children_get():
            if volelement.child_get_string("name") != checkinst["volume"]:
                continue
            voldata = ValueDict( [ (perfval.child_get_string("name"), perfval.child_get_int("value"))
                              for perfval in volelement.child_get("counters").children_get()
                              if perfval.child_get_string("name") in ('total_ops', 'other_ops',
                                  'read_ops', 'write_ops', 'read_data', 'write_data',
                                  'read_latency', 'write_latency', 'read_blocks', 'write_blocks') ] )
            voldata["timestamp"] = age
            storetime, storedata = self._load_store(checkinst["uuid"])
            if storedata is not None:
                diff = voldata - storedata["state"]
                diff /= diff["timestamp"]
                del diff["timestamp"]
            else:
                diff = None
            self._save_store(checkinst["uuid"], {
                "state": voldata
            })
            return diff, {}

        raise KeyError("Volume '%s' not found" % checkinst["volume"])
