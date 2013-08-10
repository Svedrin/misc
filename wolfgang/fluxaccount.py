# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import httplib
import base64

from urlparse import urljoin, urlparse

from wolfobject import WolfObject

class FluxAccount(WolfObject):
    objtype = "fluxaccount"

    def _request(self, url, data):
        data = json.dumps(data, indent=2)
        print "POST", data
        purl = urlparse( url )
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

        return json.loads( resp.read() )

    def submit(self, data):
        return self._request("http://fluxmon.de/submit/", data)

    def add_checks(self, data):
        return self._request("http://fluxmon.de/addchecks/", data)
