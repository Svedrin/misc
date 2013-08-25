# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
from time import time, mktime
from datetime import datetime, timedelta

from pyudev import Context, Device

from sensors.sensor import AbstractSensor
from sensors.values import ValueDict

class DiskstatsSensor(AbstractSensor):
    def discover(self):
        ctx = Context()

        def _devlink_score(link):
            if link.startswith("/dev/disk/by-uuid/"):
                return 1000
            if link.startswith("/dev/drbd/by-res/"):
                return  900
            if link.startswith("/dev/drbd/by-disk/"):
                return  800
            if link.startswith("/dev/disk/by-id/md-uuid"):
                return  900
            if link.startswith("/dev/disk/by-id/md-name"):
                return  800
            if link.startswith("/dev/disk/by-id/dm-uuid"):
                return  700
            if link.startswith("/dev/disk/by-id/dm-name"):
                return  600
            if link.startswith("/dev/disk/by-id/scsi-SATA"):
                return  500
            if link.startswith("/dev/disk/by-id/scsi"):
                return  400
            if link.startswith("/dev/disk/by-id/ata"):
                return  400
            if link.startswith("/dev/disk/by-id/wwn"):
                return  300
            return 0

        def _devname(dev):
            if "DM_VG_NAME" in dev and "DM_LV_NAME" in dev:
                return "/dev/%s/%s" % (dev["DM_VG_NAME"], dev["DM_LV_NAME"])
            currscore, currlink = 0, ""
            for link in dev.device_links:
                linkscore = _devlink_score(link)
                if linkscore > currscore:
                    currscore, currlink = linkscore, link
            if currscore > 0 and currlink:
                return currlink
            return dev.device_node

        return [ {"disk": _devname(dev)}
            for dev in ctx.list_devices()
            if (dev["SUBSYSTEM"] == "block" and
                dev["DEVTYPE"] in ("disk", "partition") and
                not dev["DEVNAME"].startswith("/dev/loop"))
        ]

    def check(self, checkinst):
        # Resolve the real device path, dereferencing symlinks as necessary.
        disk = os.path.realpath(checkinst["disk"]).replace("/dev/", "")

        # Read the state file (if possible).
        storetime, storedata = self._load_store(checkinst["uuid"])
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

        if hasattr(dev, "time_since_initialized") and dev.time_since_initialized:
            uptime = dev.time_since_initialized
        else:
            with open( "/proc/uptime" ) as ut:
                uptime = timedelta(seconds=float(ut.read().split()[0]))

        createstamp = int(mktime((datetime.now() - uptime).timetuple()))

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

        self._save_store(checkinst["uuid"], {
            "device": {
                "initialized": createstamp,
                "uuid":        dev.get("DM_UUID", None),
                "id_scsi_serial": dev.get("ID_SCSI_SERIAL", None)
            },
            "state": currstate
        })

        return diff, {}
