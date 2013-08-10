#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import socket

from time     import time, sleep
from datetime import datetime
from optparse import OptionParser

from wolfgang import WolfObjectMeta, WolfConfig
from wolfgang.prettyprint import colorprint, Colors

def main():
    parser = OptionParser(usage="%prog [options]")

    parser.add_option("-c", "--config",   default="fluxd.conf")
    parser.add_option("-d", "--datadir",  default="/var/lib/fluxmon")
    parser.add_option("-s", "--spooldir", default="/var/spool/fluxmon")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-f", "--fqdn",     default="", type="string", help="FQDN to use")

    options, posargs = parser.parse_args()
    if posargs:
        print "I don't take any positional arguments (see -h for help)."
        return 3

    wc = WolfConfig(options.config)
    wc.parse()
    wc.environ.update(options.__dict__)

    if options.fqdn:
        myhostname = options.fqdn
    else:
        myhostname = socket.getfqdn()

    if not myhostname.endswith("."):
        myhostname += '.'

    if myhostname not in wc.objects:
        return "The config doesn't seem to know me..."

    myhost = wc.objects[myhostname]

    account = wc.find_objects_by_type("fluxaccount")[0]
    print "Using account %s." % account.name

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

