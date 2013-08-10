# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import httplib
import base64

from urlparse import urljoin, urlparse

from wolfobject import WolfObject

class FluxAccount(WolfObject):
    objtype = "fluxaccount"

    def submit(self, data):
        data = json.dumps(data, indent=2)
        print "POST", data
        purl = urlparse( "http://fluxmon.de/submit/" )
        conn = {
            "http":  httplib.HTTPConnection,
            "https": httplib.HTTPSConnection
            }[purl.scheme.lower()]( purl.netloc )
        conn.putrequest( "POST", purl.path )
        conn.putheader( "Content-Type", "application/json" )
        conn.putheader( "Content-Length", str(len(data)) )
        auth = base64.encodestring('%s:%s' % (self.name, self["apikey"])).replace('\n', '')
        conn.putheader( "Authorization", "Basic %s" % auth )
        conn.endheaders()
        conn.send(data)
        resp = conn.getresponse()

        if resp.status != 200:
            fd = open("/tmp/lasterr", "wb")
            print >> fd, resp.read()
            fd.close()
            return

        respdata = json.loads( resp.read() )
        print respdata
