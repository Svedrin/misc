#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import json

from optparse import OptionParser

from sensors.sensor import SensorMeta

class DummyConf(object):
    environ = {}

def main():
    parser = OptionParser(usage="%prog [options] [<sensor>] [<parameter>=<value> ...]")

    parser.add_option("-u", "--uuid",     default="11111111-1111-1111-1111-111111111111")
    parser.add_option("-d", "--datadir",  default="/tmp")
    parser.add_option("-s", "--spooldir", default="/tmp")
    parser.add_option("-i", "--interval", default=300, type="int")
    parser.add_option("-f", "--fqdn",     default="", type="string", help="FQDN to use")

    options, posargs = parser.parse_args()

    if not posargs:
        print json.dumps(SensorMeta.sensortypes.keys(), indent=4)
        return 0

    if len(posargs) == 1:
        sensor = SensorMeta.sensortypes[posargs[0]](None)
        print json.dumps(sensor.discover(), indent=4)
        return 0

    if len(posargs) >= 2:
        DummyConf.environ.update(options.__dict__)
        params = {"uuid": options.uuid}
        for arg in posargs[1:]:
            key, val = arg.split("=", 1)
            params[key] = val
        sensor = SensorMeta.sensortypes[posargs[0]](DummyConf)
        print json.dumps(sensor.check(params), indent=4)
        return 0

if __name__ == '__main__':
    sys.exit(main())
