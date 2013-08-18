# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import subprocess

from graphunits import UnitAwareSource

class PredictingSource(UnitAwareSource):
    def define(self):
        varname = UnitAwareSource.define(self)
        self.args.append( "DEF:%s_hwpr=%s:%s:HWPREDICT"  % (varname, self.rrd.get_source_rrdpath(self.name), self.rrd.get_source_varname(self.name)) )
        self.args.append( "DEF:%s_dvpr=%s:%s:DEVPREDICT" % (varname, self.rrd.get_source_rrdpath(self.name), self.rrd.get_source_varname(self.name)) )
        self.args.append( "DEF:%s_fail=%s:%s:FAILURES"   % (varname, self.rrd.get_source_rrdpath(self.name), self.rrd.get_source_varname(self.name)) )

        self.args.append( "CDEF:%s_upper=%s_hwpr,%s_dvpr,2,*,+" % (varname, varname, varname) )
        self.args.append( "CDEF:%s_lower=%s_hwpr,%s_dvpr,2,*,-" % (varname, varname, varname) )

        return varname

    def _draw_graph(self, varname):
        self.args.append( "TICK:%s_fail#ffffa0:1.0:" % varname )
        UnitAwareSource._draw_graph(self, varname)
        self.args.append( "LINE1:%s_upper#AA0000CC:" % varname )
        self.args.append( "LINE1:%s_lower#00AA00CC:" % varname )

    def get_confidence_interval(self, start=None, end=None):
        if end is None:
            end = self.rrd.last_check
        if start is None:
            start = end - 24*60*60

        self.args = [
            "rrdtool", "graph", "/dev/null", "--start", str(int(start)), "--end", str(int(end)),
            ]
        varname = self.define()
        self.args.extend([
            "VDEF:%s_upper_last=%s_upper,LAST"    % (varname, varname),
            "VDEF:%s_lower_last=%s_lower,LAST"    % (varname, varname),
            "PRINT:%s_upper_last:upper=%%.2lf%%s" % (varname),
            "PRINT:%s_lower_last:lower=%%.2lf%%s" % (varname),
        ])

        #print '"' + '" "'.join(self.args).encode("utf-8") + '"'
        rrdtool = subprocess.Popen([arg.encode("utf-8") for arg in self.args], stdout=subprocess.PIPE)
        out, err = rrdtool.communicate()

        upper = None
        lower = None
        for line in out.split("\n"):
            if "=" in line:
                key, val = line.strip().split("=", 1)
                if key == "upper":
                    upper = float(val)
                elif key == "lower":
                    lower = float(val)
        return lower, upper


