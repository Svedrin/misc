# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import sys
import urllib
import BeautifulSoup

from sensors.sensor import AbstractSensor

class CablemodemMotorolaSensor(AbstractSensor):
    modemip  = "192.168.100.1"
    username = "admin"
    password = "motorola"

    def discover(self):
        return [{"modemip": "192.168.100.1"}]

    def check(self, checkinst):
        urllib.urlopen("http://%s/loginData.htm?loginUsername=%s&loginPassword=%s&LOGIN_BUTTON=Login" % (
            self.modemip, self.username, self.password
            ))

        html = urllib.urlopen("http://%s/cmSignalData.htm" % self.modemip).read()
        soup = BeautifulSoup.BeautifulSoup(html)

        #print soup.prettify()

        centers = soup.body.findAll("center")

        downtrs = centers[0].table.tbody.findAll("tr")
        snr = downtrs[2].findAll("td")[1].contents[0].split(' ')[0]
        downpwr = downtrs[5].findAll("td")[1].contents[0].split(' ')[0]

        uptrs = centers[1].table.tbody.findAll("tr")
        uppwr = uptrs[5].findAll("td")[1].contents[0].split(' ')[0]

        return {
            "snr":     snr,
            "downpwr": downpwr,
            "uppwr":   uppwr
        }, {}
