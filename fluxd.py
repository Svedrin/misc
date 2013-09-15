#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import socket
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
    parser.add_option("-s", "--spooldir", default="/var/spool/fluxmon")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-f", "--fqdn",     default="", type="string", help="FQDN to use")
    parser.add_option("-n", "--noop",     default=False, action="store_true", help="Only detect checks and exit, don't commit or run them")

    options, posargs = parser.parse_args()
    if posargs:
        print "I don't take any positional arguments (see -h for help)."
        return 3

    wc = WolfConfig(options.config)
    wc.parse()
    wc.environ.update(options.__dict__)

    if not os.path.exists(options.spooldir):
        return "The spool directory (%s) does not exist, please create it." % options.spooldir

    if not os.path.exists(options.datadir):
        return "The data directory (%s) does not exist, please create it." % options.datadir

    if options.fqdn:
        myhostname = options.fqdn
    else:
        myhostname = socket.getfqdn()

    if not myhostname.endswith("."):
        myhostname += '.'

    if myhostname not in wc.objects:
        return "The config doesn't seem to know me as '%s'. You may want to use -f." % myhostname

    myhost = wc.objects[myhostname]

    account = wc.find_objects_by_type("fluxaccount")[0]
    print "Using account %s." % account.name

    # Discover checkable objects
    new_checks = []
    for sensortype in SensorMeta.sensortypes:
        if sensortype not in wc.objects:
            print "Sensor type '%s' is installed but unknown to the config, skipped." % sensortype
            continue

        sensor = SensorMeta.sensortypes[sensortype](None)
        for target_params in sensor.discover():
            params = {
                "sensor": sensortype,
                "node":   myhostname,
                "target": myhostname,
            }
            params.update(target_params)
            checks = wc.find_objects_by_params("check", **params)
            if not checks:
                print "Found new target:", target_params
                check = wc.add_object("check", myhostname + ",".join(target_params.values()), [], params)
                params["uuid"] = check["uuid"]
                new_checks.append(params)
            else:
                print "Found known target:", target_params

    if options.noop:
        return "Check discovery finished but no-op is active, exiting."

    if new_checks:
        account.add_checks(new_checks)

    try:
        while True:
            nextdue = time() + options.interval
            results = []
            for chk in myhost.checks:
                checkresult = chk()
                results.append(checkresult)

            account.submit(results)

            dura = max( nextdue - time(), 5 )
            colorprint(Colors.gray, "Sleeping for %d seconds (next due %s), good night." % (dura,
                datetime.fromtimestamp(nextdue).strftime("%H:%M:%S")))
            sleep(dura)

    except KeyboardInterrupt:
        print "\nCaught ^c, shutting down."

    return 0

if __name__ == '__main__':
    sys.exit(main())

