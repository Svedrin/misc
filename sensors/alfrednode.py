# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import json
import subprocess
import logging

from time import time

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class AlfredNodeSensor(AbstractSensor):
    def discover(self, target):
        if target.name != self.conf.environ["fqdn"]:
            return []

        if not self.params["domain"].endswith("."):
            self.params["domain"] += "."

        alf = subprocess.Popen(["alfred-json", "-z", "-r", "158"], stdout=subprocess.PIPE)
        out, err = alf.communicate()
        self.nodeinfo = json.loads(out)

        self.timestamp = int(time())

        targets = []

        for macaddr, info in self.nodeinfo.items():
            fqdn = "%s.%s" % (info["hostname"], self.params["domain"])
            if fqdn not in self.conf.objects:
                self.conf.add_object("target", fqdn, [], {"macaddr": macaddr})
            elif "macaddr" not in self.conf.objects[fqdn].params or self.conf.objects[fqdn]["macaddr"] != macaddr:
                self.conf.set_object_param(self.conf.objects[fqdn]["uuid"], "macaddr", macaddr)
            targets.append({"target": fqdn})

        return targets

    def can_activate(self, checkinst):
        # targets that no longer show up in discovery may not even have a known macaddr,
        # and even if they do they won't appear in self.nodeinfo
        return "macaddr" in checkinst.target.params and \
               (not hasattr(self, "nodeinfo") or
                checkinst.target["macaddr"] in self.nodeinfo)

    def check(self, checkinst):
        if not hasattr(self, "statistics") or time() - self.timestamp > 120:
            logging.error("updating alfrednode statistics cache")
            alf = subprocess.Popen(["alfred-json", "-z", "-r", "159"], stdout=subprocess.PIPE)
            out, err = alf.communicate()
            self.statistics = json.loads(out)
            self.timestamp = int(time())

        if "macaddr" not in checkinst.target.params:
            return None, {}

        stats = self.statistics[checkinst.target["macaddr"]]

        # Read the state file (if possible).
        storetime, storedata = self._load_store(checkinst["uuid"])
        havestate = (storedata is not None)

        absstats = ValueDict({
            'clients_wifi':   stats["clients"].get("wifi", 0),
            'clients_total':  stats["clients"]["total"],
            'rootfs_usage':   stats.get("rootfs_usage", 0),
            'memory_free':    stats["memory"]["free"]    * 1024,
            'memory_total':   stats["memory"]["total"]   * 1024,
            'memory_buffers': stats["memory"]["buffers"] * 1024,
            'memory_cache':   stats["memory"]["cached"]  * 1024,
            'procs_total':    stats["processes"]["total"],
            'procs_running':  stats["processes"]["running"],
            'loadavg':        stats["loadavg"],
            })

        relstats = ValueDict({
            "tx_packets":       stats["traffic"]["tx"]["packets"],
            "tx_dropped":       stats["traffic"]["tx"]["dropped"],
            "tx_bytes":         stats["traffic"]["tx"]["bytes"],
            "rx_packets":       stats["traffic"]["rx"]["packets"],
            "rx_bytes":         stats["traffic"]["rx"]["bytes"],
            "fwd_packets":      stats["traffic"]["forward"]["packets"],
            "fwd_bytes":        stats["traffic"]["forward"]["bytes"],
            "mgmt_tx_packets":  stats["traffic"]["mgmt_tx"]["packets"],
            "mgmt_tx_bytes":    stats["traffic"]["mgmt_tx"]["bytes"],
            "mgmt_rx_packets":  stats["traffic"]["mgmt_rx"]["packets"],
            "mgmt_rx_bytes":    stats["traffic"]["mgmt_rx"]["bytes"],
            "timestamp":        self.timestamp
            })

        if havestate:
            try:
                reldiff = relstats - storedata["relstats"]
                reldiff /= reldiff["timestamp"]
                del reldiff["timestamp"]
            except ZeroDivisionError:
                merged = None
            else:
                merged = {}
                merged.update(absstats)
                merged.update(reldiff)
        else:
            merged = None

        self._save_store(checkinst["uuid"], {
            "relstats": relstats,
        })

        #return {
            #"timestamp":  self.timestamp,
            #"data":       merged,
            #"errmessage": None
        #}, {}

        return merged, {}
