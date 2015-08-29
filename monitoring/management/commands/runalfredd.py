# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import logging
import json
import socket
import subprocess

from uuid import uuid4
from time import time, sleep
from logging.handlers import SysLogHandler
from optparse import make_option

from django.core.management.base import BaseCommand

from hosts.models import Host, Domain
from monitoring.models import Sensor, Check


def getloglevel(levelstr):
    numeric_level = getattr(logging, levelstr.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % levelstr)
    return numeric_level


def doit(sensor, sensor_inst, domain, localhost):
    alf = subprocess.Popen(["alfred-json", "-z", "-r", "158"], stdout=subprocess.PIPE)
    out, err = alf.communicate()
    nodeinfo = json.loads(out)

    alf = subprocess.Popen(["alfred-json", "-z", "-r", "159"], stdout=subprocess.PIPE)
    out, err = alf.communicate()
    statistics = json.loads(out)

    # 160 = neighbor

    for macaddr, info in nodeinfo.items():
        try:
            node = Host.objects.get(fqdn__startswith=info["hostname"], domain=domain)
        except Host.DoesNotExist:
            node = Host(fqdn="%s.%s" % (info["hostname"], domain), domain=domain)
            node.save()

        try:
            check = Check.objects.get(target_host=node, sensor=sensor)
        except Check.DoesNotExist:
            check = Check(target_host=node, exec_host=localhost, sensor=sensor, uuid=str(uuid4()))
            check.save()

        print "Processing node", node.fqdn
        check.process_result( sensor_inst.process_data(check, statistics[macaddr]) )




class Command( BaseCommand ):
    help = "Daemon that periodically queries A.L.F.R.E.D. and imports its data."
    option_list = BaseCommand.option_list + (
        make_option( "-l", "--logfile",
            help="Log to a logfile.",
            default=None
            ),
        make_option( "-L", "--loglevel",
            help="loglevel of said logfile, defaults to INFO.",
            default="INFO"
            ),
        make_option( "-s", "--sysloglevel",
            help="loglevel with which to log to syslog, defaults to WARNING. OFF disables syslog altogether.",
            default="WARNING"
            ),
        make_option( "-q", "--quiet",
            help="Don't log to stdout.",
            default=False, action="store_true"
            ),
    )

    def handle(self, **options):
        os.environ["LANG"] = "en_US.UTF-8"

        try:
            import setproctitle
        except ImportError:
            pass
        else:
            setproctitle.setproctitle("fluxalfredd")

        rootlogger = logging.getLogger()
        rootlogger.name = "fluxalfredd"
        rootlogger.setLevel(logging.DEBUG)

        if not options['quiet']:
            logch = logging.StreamHandler()
            logch.setLevel({2: logging.DEBUG, 1: logging.INFO, 0: logging.WARNING}[int(options['verbosity'])])
            logch.setFormatter( logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') )
            rootlogger.addHandler(logch)

        if 'logfile' in options and options['logfile']:
            logfh = logging.FileHandler(options['logfile'])
            logfh.setLevel( getloglevel(options['loglevel']) )
            logfh.setFormatter( logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') )
            rootlogger.addHandler(logfh)

        if 'sysloglevel' in options and options['sysloglevel'].upper() != 'OFF':
            try:
                logsh = SysLogHandler(address="/dev/log")
            except socket.error, err:
                logging.error("Failed to connect to syslog: " + unicode(err))
            else:
                logsh.setLevel( getloglevel(options['sysloglevel']) )
                logsh.setFormatter( logging.Formatter('%(name)s: %(levelname)s %(message)s') )
                rootlogger.addHandler(logsh)

        class Conf(object):
            environ = {"datadir": "/var/lib/fluxmon"}

        sensor = Sensor.objects.get(name="alfrednode")
        sensor_inst = sensor.sensor(Conf())
        domain = Domain.objects.get(name="nodes", parent__name="fffd")
        localhost = Host.objects.get(fqdn__startswith=socket.getfqdn())

        try:
            while True:
                now = time()
                doit(sensor, sensor_inst, domain, localhost)
                print "I shall return, do not attempt to stop me!"
                sleep(300 - (time() - now))

        except KeyboardInterrupt:
            pass

        print "kbai"
