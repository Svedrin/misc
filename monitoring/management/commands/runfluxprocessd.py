# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os
import logging
import socket
import urlparse
import json
import pika

from logging.handlers import SysLogHandler
from optparse import make_option

from django.core.management.base import BaseCommand

from hosts.models import Host
from monitoring.models import Sensor, SensorVariable, Check, Alert

def add_check(params, user):
    try:
        check = Check.objects.get(uuid=params["uuid"])
    except Check.DoesNotExist:
        exec_host   = Host.objects.get(fqdn=params["node"])
        target_host = Host.objects.get(fqdn=params["target"])
        sensor      = Sensor.objects.get(name=params["sensor"])
        check = Check(uuid=params["uuid"], sensor=sensor, exec_host=exec_host, target_host=target_host)
        check.save()
        logging.info("Check %s created" % params["uuid"])
        for sensorparam in check.sensor.sensorparameter_set.all():
            if sensorparam.name in params:
                check.checkparameter_set.create(parameter=sensorparam, value=params[sensorparam.name])


def deactivate(params, user):
    try:
        check = Check.objects.get(uuid=params["uuid"])
    except Check.DoesNotExist:
        logging.warning("Check %s does not exist, cannot deactivate" % params["uuid"])
    else:
        check.deactivate()
        logging.info("Check %s deactivated" % params["uuid"])


def process(result, user):
    if "check" not in result:
        logging.warning("Check uuid missing")
        return
    try:
        check = Check.objects.get(uuid=result["check"])
    except Check.DoesNotExist, err:
        logging.warning("Check %s does not exist, cannot update" % result["check"])
    else:
        if True: #check.user_allowed(user):
            check.process_result(result)
            logging.info("Check %s updated" % result["check"])
        else:
            logging.warning("Check %s denied update permission to user %s" % (result["check"], user))



def on_message(channel, method_frame, header_frame, body):
    logging.debug("Message received:", body)

    try:
        data = json.loads( body )
    except ValueError, err:
        logging.error("Packet failed to decode:" + unicode(err))
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        return

    if not isinstance(data, list):
        data = [data]

    for packet in data:
        if not isinstance(packet, dict) or "type" not in packet:
            logging.error("Invalid Packet")
            continue
        try:
            if packet["type"] == "result":
                process(packet, None)
            elif packet["type"] == "add_check":
                add_check(packet, None)
            elif packet["type"] == "deactivate":
                deactivate(packet, None)
            else:
                logging.warning("Unknown packet type:" + packet["type"])
        except Exception, err:
            import traceback
            logging.error(traceback.format_exc())

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)



def getloglevel(levelstr):
    numeric_level = getattr(logging, levelstr.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % levelstr)
    return numeric_level


class Command( BaseCommand ):
    help = "Daemon that processes incoming data over RabbitMQ."
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
        make_option( "-u", "--rabbiturl",
            help="RabbitMQ URL. Default: amqp://guest:guest@127.0.0.1/fluxmon",
            default="amqp://guest:guest@127.0.0.1/fluxmon"
            ),
    )

    def handle(self, **options):
        os.environ["LANG"] = "en_US.UTF-8"

        rabbiturl  = urlparse.urlparse(options["rabbiturl"])
        if rabbiturl.scheme != "amqp":
            raise ValueError("Your URL sucks, see -h")

        rootlogger = logging.getLogger()
        rootlogger.name = "openattic_rpcd"
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

        credentials = pika.PlainCredentials(rabbiturl.username, rabbiturl.password)
        parameters  = pika.ConnectionParameters(rabbiturl.hostname, credentials=credentials)
        connection  = pika.BlockingConnection(parameters)

        channel = connection.channel()
        channel.exchange_declare(rabbiturl.path[1:], exchange_type="direct", passive=False,
                                 durable=True, auto_delete=False)
        channel.queue_declare(queue="fluxmon", auto_delete=False, durable=True)
        channel.queue_bind(queue="fluxmon", exchange=rabbiturl.path[1:], routing_key="fluxmon")
        channel.basic_qos(prefetch_count=1)

        try:
            channel.basic_consume(on_message, rabbiturl.path[1:])
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()

        connection.close()
