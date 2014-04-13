# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.db import models
from django.contrib.auth import models as auth

from mptt.models import MPTTModel, TreeForeignKey

class Domain(MPTTModel):
    name        = models.CharField(max_length=64)
    parent      = TreeForeignKey('self', null=True, blank=True, related_name='children')
    ownergroups = models.ManyToManyField(auth.Group, blank=True)
    subscribers = models.ManyToManyField(auth.User,  blank=True)

    class Meta:
        unique_together=( ('name', 'parent'), )

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        if not self.name:
            return ''
        return "%s.%s" % (self.name, unicode(self.parent) if self.parent is not None else '')

class Host(models.Model):
    fqdn        = models.CharField(max_length=255, unique=True)
    domain      = TreeForeignKey(Domain)
    subscribers = models.ManyToManyField(auth.User, blank=True)

    @property
    def config(self):
        return "node %s\n" % self.fqdn

    def __unicode__(self):
        return self.fqdn
