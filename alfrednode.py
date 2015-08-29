# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from time import time

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class AlfredNodeSensor(AbstractSensor):
    def discover(self, target):
        return []

    def check(self, checkinst):
        pass

    def process_data(self, checkinst, stats):
        # Read the state file (if possible).
        storetime, storedata = self._load_store(checkinst.uuid)
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
            "timestamp":  time()
            })

        if havestate:
            reldiff = relstats - storedata["relstats"]
            reldiff /= reldiff["timestamp"]
            del reldiff["timestamp"]
            merged = {}
            merged.update(absstats)
            merged.update(reldiff)
        else:
            merged = None

        self._save_store(checkinst.uuid, {
            "relstats": relstats,
        })

        return {
            "timestamp":  int(time()),
            "data":       merged,
            "errmessage": None
        }
