# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.db import models
from django.contrib.auth import models as auth

class Domain(models.Model):
    name        = models.CharField(max_length=64)
    parent      = models.ForeignKey('self', null=True, blank=True)
    ownergroups = models.ManyToManyField(auth.Group)
    subscribers = models.ManyToManyField(auth.User)

class Host(models.Model):
    fqdn        = models.CharField(max_length=255)
    domain      = models.ForeignKey(Domain)
    subscribers = models.ManyToManyField(auth.User)
