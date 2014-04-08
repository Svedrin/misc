#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import json
import socket

from optparse import OptionParser

from sensors.sensor import SensorMeta


class Target(dict):
    name = ""

class DummyConf(object):
    environ = {}

class DummyParams(dict):
    target = Target()


def main():
    parser = OptionParser(usage="%prog [options] [<sensor>] [target.<parameter>=<value> ...] [<parameter>=<value> ...]")

    parser.add_option("-u", "--uuid",     default="11111111-1111-1111-1111-111111111111")
    parser.add_option("-d", "--datadir",  default="/tmp")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-f", "--fqdn",     default=socket.getfqdn(), type="string", help=("FQDN to use (defaults to %s)" % socket.getfqdn()))
    parser.add_option("-t", "--target",   default=None, help="Target Host FQDN (defaults to --fqdn)")

    options, posargs = parser.parse_args()

    if not options.fqdn.endswith("."):
        options.fqdn += '.'
    if not options.target:
        options.target = options.fqdn
    if not options.target.endswith("."):
        options.target += '.'

    DummyConf.environ.update(options.__dict__)

    params = DummyParams({"uuid": options.uuid})
    params.target.name = options.target
    for arg in posargs[1:]:
        key, val = arg.split("=", 1)
        if key.startswith("target."):
            _, tgtkey = key.split(".", 1)
            params.target[tgtkey] = val
        else:
            params[key] = val

    if not posargs:
        print json.dumps(SensorMeta.sensortypes.keys(), indent=4)
        return 0

    if len(params) == 1:
        sensor = SensorMeta.sensortypes[posargs[0]](DummyConf)
        print json.dumps(sensor.discover(params.target), indent=4)
        return 0

    if len(params) >= 2:
        sensor = SensorMeta.sensortypes[posargs[0]](DummyConf)
        print json.dumps(sensor.check(params), indent=4)
        return 0

if __name__ == '__main__':
    sys.exit(main())
