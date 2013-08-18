# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import os.path
import re
import subprocess
import datetime

from time import time

from django.conf import settings

# Python2.6 fallback. see http://docs.python.org/2/library/datetime#datetime.timedelta.total_seconds
if hasattr(datetime.timedelta, "total_seconds"):
    timedelta = datetime.timedelta
else:
    class timedelta(datetime.timedelta):
        def total_seconds(self):
            return (self.microseconds + (self.seconds + self.days * 24 * 3600) * 10**6) / 10**6


def intsecs(**kwargs):
    return int(timedelta(**kwargs).total_seconds())


def mkrra(baseres, rratype, rrares, rrakeep):
    rraintv = rrares  / baseres
    rragens = rrakeep / rrares
    return "RRA:%s:0.5:%d:%d" % ( rratype, rraintv, rragens )

def mkpred(baseres, rratype, predictlen, seasonlen, alpha, beta):
    predictnum = predictlen / baseres
    seasonnum  = seasonlen  / baseres
    return "RRA:%s:%d:%f:%f:%d" % (rratype, predictnum, alpha, beta, seasonnum)

def dictset(dct, varname, value):
    # ds[ping].last_ds -> {"ds": {"ping": {"last_ds": value} } }
    if "." in varname:
        key, rest = varname.split(".", 1)
        if "[" in key:
            # treat keys given by [] as if they had been given using . notation,
            # by rewriting key and rest accordingly.
            key, dictkey = key[:-1].split("[")
            rest = "%s.%s" % (dictkey, rest)
        if key not in dct:
            dct[key] = {}
        dictset(dct[key], rest, value)
    else:
        dct[varname] = value



class RRD(object):
    def __init__(self, check):
        self.check = check
        self.rrdpath = os.path.join(settings.RRDDIR, "%s.rrd" % check.uuid)
        if os.path.exists(self.rrdpath):
            self.last_check = int(os.path.getmtime(self.rrdpath))
        else:
            self.last_check = int(time())
        self.service_description = "Need sum srs service descripshun"
        self._info = None

    def get_source(self, srcname):
        from graphunits import UnitAwareSource
        return UnitAwareSource( self, srcname )

    def get_source_varname(self, srcname):
        return srcname[:19]

    def get_source_label(self, srcname):
        var = self.check.sensor.sensorvariable_set.get(name=srcname)
        varname = var.display if var.display else var.name
        if var.unit:
            return "%s [%s]" % (varname, var.unit)
        return varname

    def get_source_perfdata(self, srcname):
        return self.info["ds"][srcname]["last_ds"]

    def get_source_rrdpath(self, srcname):
        return self.rrdpath

    @property
    def last_update(self):
        if os.path.exists(self.rrdpath):
            return datetime.datetime.fromtimestamp(os.path.getmtime(self.rrdpath))
        return None

    def update(self, result):
        if result["timestamp"] > self.last_check:
            self.last_check = int(result["timestamp"])

        data = result["data"]

        if not os.path.exists(self.rrdpath):
            if result["errmessage"] is not None:
                print "Not *creating* new RRD from bogus data."
                return
            res = intsecs(seconds=300)
            args = [ "rrdtool", "create", self.rrdpath, "-s", str(res) ]
            for dsname in data:
                args.append('DS:%s:GAUGE:600:U:U' % dsname[:19])
            args.extend([
                # Shamelessly stolen from Munin
                #           RRA type,  resolution,          max record age
                mkrra( res, "AVERAGE", res,                 intsecs(days=7) ),
                mkrra( res, "MIN",     res,                 intsecs(days=7) ),
                mkrra( res, "MAX",     res,                 intsecs(days=7) ),
                mkrra( res, "AVERAGE", intsecs(minutes=30), intsecs(days=14) ),
                mkrra( res, "MIN",     intsecs(minutes=30), intsecs(days=14) ),
                mkrra( res, "MAX",     intsecs(minutes=30), intsecs(days=14) ),
                mkrra( res, "AVERAGE", intsecs(hours=2),    intsecs(days=45) ),
                mkrra( res, "MIN",     intsecs(hours=2),    intsecs(days=45) ),
                mkrra( res, "MAX",     intsecs(hours=2),    intsecs(days=45) ),
                mkrra( res, "AVERAGE", intsecs(days=1),     intsecs(days=450) ),
                mkrra( res, "MIN",     intsecs(days=1),     intsecs(days=450) ),
                mkrra( res, "MAX",     intsecs(days=1),     intsecs(days=450) ),
                #           RRA type,     prediction time,  season length,    alpha,   beta
                mkpred(res, "HWPREDICT",  intsecs(days=5),  intsecs(days=1),  0.5,     0.5 ),
                ])
            rrdtool = subprocess.Popen(args)
            rrdtool.communicate()

        for key in data:
            data[key] = re.findall("(\d*(\.\d*)?)", unicode(data[key]).encode("UTF-8"))[0][0]

        args = [ "rrdtool", "update", self.rrdpath ]
        names, values = zip( *(data.items()) )
        args.extend([ "--template", ":".join([ dsname[:19] for dsname in names ]),
            ":".join( [str(x) for x in ([result["timestamp"]] + list(values))] )
            ])
        rrdtool = subprocess.Popen(args, env={"TZ": "UTC"})
        rrdtool.communicate()
        if rrdtool.returncode != 0:
            print "RRDtool update failed for %s" % self.rrdpath

    @property
    def info(self):
        if self._info is not None:
            return self._info
        if not os.path.exists(self.rrdpath):
            return None
        args = [ "rrdtool", "info", self.rrdpath ]
        rrdtool = subprocess.Popen(args, stdout=subprocess.PIPE, env={"LANG": "C"})
        out, err = rrdtool.communicate()

        data = {}
        for line in out.split("\n"):
            if not line:
                continue
            varname, value = line.split(" = ")
            if value[0] == value[-1] == '"':
                # if a value is "quoted", remove them
                value = value[1:-1]
            dictset(data, varname, value)
        self._info = data
        return data
