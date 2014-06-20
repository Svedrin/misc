#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import sys
import socket
import logging
import os.path

from time     import time
from datetime import datetime
from optparse import OptionParser

from Crypto.PublicKey   import RSA
from Crypto             import Random

from wolfgang import WolfConfig
from wolfgang.prettyprint import colorprint, Colors
from sensors.sensor import SensorMeta

def main():
    parser = OptionParser(usage="%prog [options]")

    parser.add_option("-1", "--oneshot",  default=False, action="store_true")
    parser.add_option("-c", "--config",   default="fluxd.conf")
    parser.add_option("-d", "--datadir",  default="/var/lib/fluxmon")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-k", "--keygen",   default=False, action="store_true",
                            help="Only generate private and public keys and then exit.")
    parser.add_option("-l", "--logfile",  default="", type="string",
                            help="Redirect log output to a file.")
    parser.add_option("-f", "--fqdn",     default=socket.getfqdn(), type="string",
                            help=("FQDN to use (defaults to %s)" % socket.getfqdn()))
    parser.add_option("-n", "--noop",     default=False, action="store_true",
                            help="Only detect checks and exit, don't commit or run them")
    parser.add_option("-v", "--verbose",  default=0, action="count", help="Increase verbosity")

    options, posargs = parser.parse_args()
    if posargs:
        print "I don't take any positional arguments (see -h for help)."
        return 3

    rootlogger = logging.getLogger()
    rootlogger.name = "fluxd"
    rootlogger.setLevel(logging.DEBUG)

    if options.logfile:
        logch = logging.FileHandler(options.logfile)
    else:
        logch = logging.StreamHandler()
    logch.setLevel({3: logging.DEBUG, 2: logging.INFO, 1: logging.WARNING, 0: logging.ERROR}.get(int(options.verbose), logging.DEBUG))
    logch.setFormatter( logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') )
    rootlogger.addHandler(logch)

    keysdir = os.path.join( os.path.dirname(options.config), ".keys" )
    if options.keygen or not os.path.exists(keysdir):
        if not os.path.exists(keysdir):
            os.mkdir(keysdir)
        os.chmod(keysdir, 0700)
        rng = Random.new().read
        print "Generating keys. This may or may not take some time."
        privkey = RSA.generate(4096, rng)
        with open(os.path.join(keysdir, "id_rsa_4096"), "wb") as fp:
            fp.write(privkey.exportKey())
            fp.write("\n")
        with open(os.path.join(keysdir, "id_rsa_4096.pub"), "wb") as fp:
            fp.write(privkey.publickey().exportKey())
            fp.write("\n")
        print "Generation complete, keys have been saved in %s." % keysdir
        print "Please register the key at fluxmon.de and configure the fluxaccount in fluxd.conf before proceeding."
        return 255

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
    logging.info("Using account %s.", account.name)

    # Discover checkable objects
    all_checks = []
    for sensortype in SensorMeta.sensortypes:
        if sensortype not in wc.objects:
            logging.warning("Sensor type '%s' is installed but unknown to the config, skipped.",
                sensortype)
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
                    logging.warning("Found new target on %s: %s", confobj.name, target_params)
                    checkname = ",".join([confobj.name, sensortype] + target_params.values())
                    check = wc.add_object("check", checkname, [], params)
                    params["uuid"] = check["uuid"]
                else:
                    logging.info("Found known target on %s: %s", confobj.name, target_params)
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

            if options.oneshot:
                break

            dura = max( nextdue - time(), 5 )
            colorprint(Colors.gray, "Sleeping for %d seconds (next due %s), good night." % (dura,
                datetime.fromtimestamp(nextdue).strftime("%H:%M:%S")))
            account.sleep(dura)

    except KeyboardInterrupt:
        print "\nCaught ^c, shutting down."

    return 0

if __name__ == '__main__':
    sys.exit(main())

