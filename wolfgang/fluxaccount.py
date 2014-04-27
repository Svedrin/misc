# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import pika

from urlparse import urljoin, urlparse
from time import sleep

from wolfobject import WolfObject

class FluxAccount(WolfObject):
    objtype = "fluxaccount"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)
        rabbiturl   = urlparse(params["rabbiturl"])
        credentials = pika.PlainCredentials(rabbiturl.username, rabbiturl.password)
        parameters  = pika.ConnectionParameters(rabbiturl.hostname, credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel    = self.connection.channel()
        self.exchange   = rabbiturl.path[1:]

        channel.exchange_declare(self.exchange,
            exchange_type = "direct",
            passive       = False,
            durable       = True,
            auto_delete   = False)
        channel.queue_declare(queue="fluxmon",
            auto_delete   = False,
            durable       = True)
        channel.queue_bind(queue="fluxmon", exchange=self.exchange, routing_key="fluxmon")

    def _request(self, data):
        data = json.dumps(data)
        self.channel.basic_publish(exchange=self.exchange,
            routing_key='fluxmon',
            body=data,
            properties=pika.BasicProperties(
                delivery_mode = 2  # make message persistent
            )
        )

    def sleep(self, dura):
        if hasattr(self.connection, "sleep"):
            self.connection.sleep(dura)
        else:
            sleep(dura)

    def submit(self, data):
        for thing in data:
            thing["type"] = "result"
        return self._request(data)

    def deactivate(self, check):
        return self._request({
            "type": "deactivate",
            "uuid": check["uuid"]
        })

    def add_checks(self, data):
        for thing in data:
            thing["type"] = "add_check"
        return self._request(data)
