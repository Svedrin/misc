# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json

from urlparse import urljoin, urlparse

from wolfobject import WolfObject

try:
    import requests
except ImportError:
    import os
    import httplib
    import base64
    if "http_proxy" in os.environ:
        raise

    from wolfgang.prettyprint import colorprint, Colors
    colorprint(Colors.red, "The requests module is not available. You don't seem to require a proxy, so I'm gonna work around this. If you do, you need to install requests.")

    class ReqResponse(object):
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    class requests(object):
        @classmethod
        def post(cls, url, data, auth, headers):
            purl = urlparse( url )
            conn = {
                "http":  httplib.HTTPConnection,
                "https": httplib.HTTPSConnection
                }[purl.scheme.lower()]( purl.netloc )
            conn.putrequest( "POST", purl.path )
            for key, val in headers.items():
                conn.putheader( key, val )
            auth = base64.encodestring(':'.join(auth)).replace('\n', '')
            conn.putheader( "Authorization", "Basic %s" % auth )
            conn.endheaders()
            conn.send(data)
            resp = conn.getresponse()
            return ReqResponse(resp.status, resp.read())


class FluxAccount(WolfObject):
    objtype = "fluxaccount"

    def _request(self, url, data):
        data = json.dumps(data, indent=2)
        print "POST", data

        resp = requests.post(url, data=data, auth=(self.name, self["apikey"]), headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
        })

        if resp.status_code != 200:
            fd = open("/tmp/lasterr", "wb")
            print >> fd, resp.text
            fd.close()
            return

        respdata = json.loads( resp.text )
        print respdata
        return respdata

    def submit(self, data):
        return self._request("http://fluxmon.de/submit/results/", data)

    def add_checks(self, data):
        return self._request("http://fluxmon.de/submit/checks/", data)
