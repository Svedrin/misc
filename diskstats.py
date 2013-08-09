# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
from time import time, mktime
from datetime import datetime

from pyudev import Context, Device

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class DiskstatsSensor(AbstractSensor):
    def discover(self):
        ctx = Context()

        def _devname(dev):
            if "DM_VG_NAME" in dev and "DM_LV_NAME" in dev:
                return "/dev/%s/%s" % (dev["DM_VG_NAME"], dev["DM_LV_NAME"])
            return dev.device_node

        return [ _devname(dev)
            for dev in ctx.list_devices()
            if (dev["SUBSYSTEM"] == "block" and
                dev["DEVTYPE"] in ("disk", "partition") and
                not dev["DEVNAME"].startswith("/dev/loop"))
        ]

    def check(self, disk):
        # Resolve the real device path, dereferencing symlinks as necessary.
        disk = os.path.realpath(disk).replace("/dev/", "")

        # Read the state file (if possible).
        storetime, storedata = self._load_store()
        havestate = (storedata is not None)

        ctx = Context()
        dev = Device.from_name(ctx, "block", disk)

        # <http://www.mjmwired.net/kernel/Documentation/block/stat.txt>
        currstate = ValueDict(zip((
            "rd_ios", "rd_merges", "rd_sectors", "rd_ticks",
            "wr_ios", "wr_merges", "wr_sectors", "wr_ticks",
            "ios_in_prog", "tot_ticks", "rq_ticks"
        ), [
            int(count) for count in dev.attributes["stat"].strip().split()
        ]))
        currstate["timestamp"] = time()

        # Sanity-Check the state file. We expect the Device UUID and creation timestamp to
        # match those from the statfile (if possible).

        try:
            createstamp = int(mktime((datetime.now() - dev.time_since_initialized).timetuple()))
        except AttributeError:
            createstamp = None

        if havestate:
            if "device" not in storedata:
                havestate = False

            if createstamp != storedata["device"]["initialized"]:
                havestate = False

            if dev.get("DM_UUID", None) != storedata["device"]["uuid"]:
                havestate = False

            if dev.get("ID_SCSI_SERIAL", None) != storedata["device"]["id_scsi_serial"]:
                havestate = False

        if havestate:
            diff = currstate - storedata["state"]
            diff /= diff["timestamp"]
            del diff["timestamp"]
            # ios_in_prog is the only value which is not a counter
            diff["ios_in_prog"] = currstate["ios_in_prog"]
            # scale the ticks to seconds so RRDtool will use the correct scale factors
            diff = diff.scale({
                "rd_ticks":  1000 ** -1,
                "wr_ticks":  1000 ** -1,
                "rq_ticks":  1000 ** -1,
                "tot_ticks": 1000 ** -1,
            })
        else:
            diff = None

        self._save_store({
            "device": {
                "initialized": createstamp,
                "uuid":        dev.get("DM_UUID", None),
                "id_scsi_serial": dev.get("ID_SCSI_SERIAL", None)
            },
            "state": currstate
        })

        return diff, {}
