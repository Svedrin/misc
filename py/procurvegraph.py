#!/usr/bin/env python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import gv

from pyasn1.type.univ                   import ObjectIdentifier
from pysnmp.entity.rfc3413.oneliner     import cmdgen
from pysnmp.proto.rfc1902               import Counter32, Counter64, Integer, Integer32, OctetString

from pygraph.readwrite.dot		import write
from pygraph.classes.digraph		import digraph
from pygraph.algorithms.searching	import breadth_first_search

PROCURVE_OIDS = {
    "system-info": "1.3.6.1.2.1.1",
    "system-mac":  "1.3.6.1.2.1.17.1.1.0",
    "cdp-neigh":   "1.3.6.1.4.1.9.9.23.1.2.1.1",
}

class SnmpError(Exception):
    pass

def snmp_to_python(thing):
    if isinstance(thing, OctetString):
        return thing.prettyPrint()
    if isinstance(thing, (Counter32, Counter64, Integer, Integer32)):
        return int(thing)
    if isinstance(thing, ObjectIdentifier):
        return str(thing)
    return thing

def switchquery(addr, oid):
    scope = [int(x) for x in oid.split(".")]

    cmdGen = cmdgen.CommandGenerator()
    if scope[-1] == 0:
        cmd = cmdGen.getCmd
    else:
        cmd = cmdGen.nextCmd
    errorIndication, errorStatus, errorIndex, varBinds = cmd(
        cmdgen.CommunityData('admin'),
        cmdgen.UdpTransportTarget((addr, 161)),
        oid
    )

    if errorIndication:
        raise SnmpError(errorIndication)
    if errorStatus:
        raise SnmpError('%s at %s' % (
            errorStatus.prettyPrint(),
            errorIndex and varBinds[int(errorIndex)-1] or '?'
            )
        )

    if scope[-1] == 0:
        return snmp_to_python(varBinds[0][1])

    result = {}
    def get_result_scope(oid):
        resscope = result
        for x in list(oid)[len(scope):]:
            if x not in resscope:
                resscope[x] = {}
            resscope = resscope[x]
        return resscope

    for bind in varBinds:
        for key, value in bind:
            get_result_scope(key)[0] = snmp_to_python(value)

    return result

def switchgraph(switchaddrs, outfile):
    gr = digraph()

    nodes = {}
    edges = {}

    for addr in switchaddrs:
        print >> sys.stderr, "Querying %s..." % addr
        try:
            sysmac = switchquery(addr, PROCURVE_OIDS["system-mac"])
        except SnmpError, err:
            print >> sys.stderr, unicode(err)
            continue
        nodes[sysmac] = addr

        cdpneigh = switchquery(addr, PROCURVE_OIDS["cdp-neigh"])
        if not cdpneigh:
            print >> sys.stderr, "%s didn't return any data!" % addr
            continue
        for port in cdpneigh[6]:
            if 1 in cdpneigh[6][port]:
                othermac = cdpneigh[6][port][1][0]
            else:
                continue
            if othermac not in nodes:
                nodes[othermac] = "%s\n%s" % (othermac[2:], cdpneigh[8][port][1][0][:20])
            if (sysmac, othermac) not in edges and (othermac, sysmac) not in edges:
                edges[(sysmac, othermac)] = (port, cdpneigh[7][port][1][0])

    for nodemac, nodeaddr in nodes.items():
        gr.add_node( nodemac, attrs=(
            ( "label", r"%s" % nodeaddr ),
            ( "shape", "diamond" ),
            ) )

    for edgemacs, edgeports in edges.items():
        gr.add_edge( (edgemacs[0], edgemacs[1]), attrs=(
            ( "taillabel", edgeports[0] ),
            ( "headlabel", edgeports[1] ),
            ( "dir", "none" ),
            ) )

    dot = write(gr)
    if outfile == "-":
        print dot
    elif outfile.endswith(".dot"):
        fd = open(outfile, "wb")
        fd.write(dot)
        fd.close()
        print "Wrote output to %s." % outfile
    else:
        outfmt = outfile.rsplit(".", 1)
        gvv = gv.readstring(dot)
        gv.layout(gvv, 'fdp')
        gv.render(gvv, outfmt, outfile)
        print "Wrote output to %s." % outfile

def main():
    if len(sys.argv) < 3:
        return ("Usage: %s <switch ...> <outfile>\n"
                "Name as many switches as you want. If <outfile> ends in '.dot', a dotfile "
                "will be written, otherwise we will try to render it as an image."
               ) % sys.argv[0]

    switchaddrs = sys.argv[1:-1]
    outfile = sys.argv[-1]
    return switchgraph(switchaddrs, outfile)

if __name__ == '__main__':
    sys.exit(main())
