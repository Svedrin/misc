# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from django.db import models
from django.contrib.auth.models import User

class PublicKey(models.Model):
    owner       = models.ForeignKey(User)
    uuid        = models.CharField(max_length=37)
    description = models.CharField(max_length=255)
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
