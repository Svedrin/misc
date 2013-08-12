# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import requests

from urlparse import urljoin, urlparse

from wolfobject import WolfObject

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
