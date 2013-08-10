# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from django.db import models
from django.contrib.auth import models as auth

class ApiKey(models.Model):
    owner       = models.ForeignKey(auth.User)
    apikey      = models.CharField(max_length=40)
    description = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if not self.apikey:
            self.apikey = str(uuid.uuid4())
        models.Model.save(self, *args, **kwargs)

    @property
    def config(self):
        return "fluxaccount %s apikey=%s\n" % (self.owner.username, self.apikey)
