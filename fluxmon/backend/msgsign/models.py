# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from django.db import models
from django.contrib.auth.models import User

from hosts.models import Host

class PublicKey(models.Model):
    owner       = models.ForeignKey(User)
    host        = models.ForeignKey(Host, unique=True)
    uuid        = models.CharField(max_length=37, unique=True)
    description = models.CharField(max_length=255, blank=True)
    active      = models.BooleanField(default=True)
    publickey   = models.TextField()

    class InvalidSignature(ValueError):
        pass

    @property
    def keyobj(self):
        return RSA.importKey(self.publickey)

    def verify(self, message, sigstr):
        msghash = SHA256.new(message).digest()
        if not self.keyobj.verify(msghash, (int(sigstr),)):
            raise PublicKey.InvalidSignature()

    @property
    def config(self):
        return 'fluxaccount %s key=%s rabbiturl="amqp://fluxmon:fluxmon@fluxmon.de/fluxmon"\n' % (self.owner.username, self.uuid)
