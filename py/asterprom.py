#!/usr/bin/env python

import re
import socket
import sys

from time import time


"""
Connects to Asterisk via the Asterisk Management Interface, queries SIP and IAX
peers and exports them to stdout via the Prometheus text format.

Prerequisites:

* Enable AMI like described here:
  http://the-asterisk-book.com/1.6/asterisk-manager-api.html

* Install prometheus-node-exporter and enable the textfile collector.
  On Debian, you can apt-get install prometheus-node-exporter and add this
  to the $ARGS variable in /etc/default/prometheus-node-exporter:

  --collector.textfile.directory=/var/lib/prometheus/node-exporter

* Add a cron job that regularly runs asterprom:

  * * * * * python3 /usr/local/bin/asterprom.py admin secret5 > /var/lib/prometheus/node-exporter/asterisk.prom

* Point Prometheus to the node exporter.

"""


def latency_from_status(status):
    m = re.match(r"OK \((\d+) ms\)", status)
    if m is None:
        raise ValueError("status is not OK, latency is unknown")
    return float(m.group(1)) * 0.001


class LoginFailed(Exception):
    pass


class AsteriskManager(object):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)
        self.buf = ""

    def connect(self, addr):
        self.sock.connect(addr)

        if not self.sock.recv(1024).startswith(b"Asterisk Call Manager"):
            raise ValueError("this doesn't look like an Asterisk instance")

    def send_part(self, params):
        data = "\r\n".join( "%s: %s" % item for item in params.items() ) + "\r\n\r\n"
        self.sock.send(data.encode('utf-8'))

    def recv_part(self):
        while "\r\n\r\n" not in self.buf:
            self.buf += self.sock.recv(1024).decode("utf-8")
        part_lines, self.buf = self.buf.split("\r\n\r\n", 1)
        return dict(line.split(": ", 1)
            for line in part_lines.split("\r\n")
        )

    def cmd(self, params):
        self.send_part(params)
        response = self.recv_part()

        if response.get("EventList") == "start":
            entries = []
            while True:
                next_part = self.recv_part()
                if next_part.get("EventList") == "Complete":
                    break
                entries.append(next_part)
            return entries

        return response

    def login(self, username, password):
        resp = self.cmd({
            "Action":   "Login",
            "Events":   "off",
            "Username": username,
            "Secret":   password,
        })
        if resp["Response"] != "Success":
            raise LoginFailed(resp["Message"])

    @property
    def iax_peers(self):
        return self.cmd({ "Action": "IAXpeers" })

    @property
    def sip_peers(self):
        return self.cmd({ "Action": "SIPpeers" })

    @property
    def sip_registry(self):
        return self.cmd({ "Action": "SIPshowregistry" })


def main():
    if len(sys.argv) != 3:
        print("Usage: asterprom.py <username> <password>")
        return 1

    ami = AsteriskManager()
    ami.connect(('127.0.0.1', 5038))
    ami.login(sys.argv[1], sys.argv[2])

    for peer in ami.iax_peers:
        kwds = 'channel_type="%(Channeltype)s",name="%(ObjectName)s",description="%(Description)s"' % peer
        if peer["Status"].startswith("OK"):
            print( 'iax_peer_ok{%s} 1' % kwds )
            print( 'iax_peer_latency{%s} %f' % (kwds, latency_from_status(peer["Status"])) )
        else:
            print( 'iax_peer_ok{%s} 0' % kwds )

    for peer in ami.sip_peers:
        kwds = 'channel_type="%(Channeltype)s",name="%(ObjectName)s",description="%(Description)s"' % peer
        if peer["Status"].startswith("OK"):
            print( 'sip_peer_ok{%s} 1' % kwds )
            print( 'sip_peer_latency{%s} %f' % (kwds, latency_from_status(peer["Status"])) )
        else:
            print( 'sip_peer_ok{%s} 0' % kwds )

    for peer in ami.sip_registry:
        kwds = 'host="%(Host)s",username="%(Username)s@%(Domain)s"' % peer
        if peer["State"] == "Registered":
            print( 'sip_peer_registered{%s} 1' % kwds )
            print( 'sip_peer_registration_age{%s} %f' % (kwds, time() - int(peer["RegistrationTime"])) )
        else:
            print( 'sip_peer_registered{%s} 0' % kwds )


if __name__ == '__main__':
    main()
