# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

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
        self.args.append( "TICK:%s_fail#FAF2CC:1.0:" % varname )
        UnitAwareSource._draw_graph(self, varname)
        self.args.append( "LINE1:%s_upper#AA0000CC:" % varname )
        self.args.append( "LINE1:%s_lower#00AA00CC:" % varname )


