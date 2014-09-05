# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os.path
import json
import pika

from Crypto.Hash        import SHA256
from Crypto.PublicKey   import RSA
from Crypto             import Random

from urlparse import urljoin, urlparse
from time import sleep

from wolfobject import WolfObject

def chunks(l, n):
    """ Yield successive n-sized chunks from l. """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class FluxAccount(WolfObject):
    objtype = "fluxaccount"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)
        rabbiturl   = urlparse(params["rabbiturl"])
        credentials = pika.PlainCredentials(rabbiturl.username, rabbiturl.password)
        parameters  = pika.ConnectionParameters(rabbiturl.hostname, credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel    = self.connection.channel()
        self.exchange   = str(rabbiturl.path[1:])

        try:
            self.channel.exchange_declare(
                exchange      = self.exchange,
                exchange_type = "direct",
                passive       = True,
                durable       = True,
                auto_delete   = False)
        except TypeError:
            self.channel.exchange_declare(
                exchange      = self.exchange,
                type          = "direct",
                passive       = True,
                durable       = True,
                auto_delete   = False)
        self.channel.queue_declare(
            queue         = "fluxmon",
            auto_delete   = False,
            passive       = True,
            durable       = True)

        self.privkey = None

    def _load_key(self):
        keysdir = os.path.join( os.path.dirname(self._conf.environ["config"]), ".keys" )
        self.rng = Random.new().read

        with open(os.path.join(keysdir, "id_rsa_4096"), "rb") as fp:
            self.privkey = RSA.importKey(fp.read())

    def _request(self, data):
        data = json.dumps(data)

        if self.privkey is None:
            self._load_key()

        msghash = SHA256.new(data).digest()
        sig     = self.privkey.sign(msghash, self.rng)
        sigstr  = str(sig[0])
        data = json.dumps({
            "data": data,
            "sig":  sigstr,
            "key":  self.params["key"]
        })

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
        for datachunk in chunks(data, 50):
            self._request(datachunk)

    def deactivate(self, check):
        self._request({
            "type": "deactivate",
            "uuid": check["uuid"]
        })

    def add_checks(self, data):
        for thing in data:
            thing["type"] = "add_check"
        for datachunk in chunks(data, 50):
            self._request(datachunk)
