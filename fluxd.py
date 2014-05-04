#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import socket
import logging
import os.path

from time     import time, sleep
from datetime import datetime
from optparse import OptionParser

from wolfgang import WolfObjectMeta, WolfConfig
from wolfgang.prettyprint import colorprint, Colors
from sensors.sensor import SensorMeta

def main():
    parser = OptionParser(usage="%prog [options]")

    parser.add_option("-c", "--config",   default="fluxd.conf")
    parser.add_option("-d", "--datadir",  default="/var/lib/fluxmon")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-f", "--fqdn",     default=socket.getfqdn(), type="string", help=("FQDN to use (defaults to %s)" % socket.getfqdn()))
    parser.add_option("-n", "--noop",     default=False, action="store_true", help="Only detect checks and exit, don't commit or run them")
    parser.add_option("-v", "--verbose",  default=0, action="count", help="Increase verbosity")

    options, posargs = parser.parse_args()
    if posargs:
        print "I don't take any positional arguments (see -h for help)."
        return 3

    rootlogger = logging.getLogger()
    rootlogger.name = "fluxd"
    rootlogger.setLevel(logging.DEBUG)

    if options.verbose:
        logch = logging.StreamHandler()
        logch.setLevel({2: logging.DEBUG, 1: logging.INFO, 0: logging.WARNING}[int(options.verbose)])
        logch.setFormatter( logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') )
        rootlogger.addHandler(logch)

    wc = WolfConfig(options.config)
    wc.parse()

    if not options.fqdn.endswith("."):
        options.fqdn += '.'

    wc.environ.update(options.__dict__)

    if not os.path.exists(options.datadir):
        return "The data directory (%s) does not exist, please create it." % options.datadir

    myhostname = options.fqdn

    if myhostname not in wc.objects:
        return "The config doesn't seem to know me as '%s'. You may want to use -f." % myhostname

    myhost = wc.objects[myhostname]

    account = wc.find_objects_by_type("fluxaccount")[0]
    logging.info("Using account %s." % account.name)

    # Discover checkable objects
    all_checks = []
    for sensortype in SensorMeta.sensortypes:
        if sensortype not in wc.objects:
            logging.warning("Sensor type '%s' is installed but unknown to the config, skipped." % sensortype)
            continue

        sensor = SensorMeta.sensortypes[sensortype](wc)

        for confobj in wc.objects.values():
            if confobj.objtype not in ("node", "target"):
                continue
            for target_params in sensor.discover(confobj):
                params = {
                    "sensor": sensortype,
                    "node":   myhostname,
                    "target": confobj.name,
                }
                params.update(target_params)
                checks = wc.find_objects_by_params("check", **params)
                if not checks:
                    logging.warning( "Found new target on %s: %s" % (confobj.name, target_params) )
                    checkname = ",".join([confobj.name, sensor.name] + target_params.values())
                    check = wc.add_object("check", checkname, [], params)
                    params["uuid"] = check["uuid"]
                else:
                    logging.info( "Found known target on %s: %s" % (confobj.name, target_params) )
                    params["uuid"] = checks[0]["uuid"]
                all_checks.append(params)

    if options.noop:
        return "Check discovery finished but no-op is active, exiting."

    if all_checks:
        account.add_checks(all_checks)

    for chk in myhost.checks:
        if not chk.is_active:
            account.deactivate(chk)

    try:
        while True:
            nextdue = time() + options.interval
            results = []
            for chk in myhost.checks:
                if chk.is_active:
                    checkresult = chk()
                    results.append(checkresult)

            account.submit(results)

            dura = max( nextdue - time(), 5 )
            colorprint(Colors.gray, "Sleeping for %d seconds (next due %s), good night." % (dura,
                datetime.fromtimestamp(nextdue).strftime("%H:%M:%S")))
            account.sleep(dura)

    except KeyboardInterrupt:
        print "\nCaught ^c, shutting down."

    return 0

if __name__ == '__main__':
    sys.exit(main())

