# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from django.db import models

from hosts import models as hosts
from sensors.sensor import SensorMeta

class Sensor(models.Model):
    name        = models.CharField(max_length=255)

    @property
    def sensor(self):
        return SensorMeta.sensortypes[self.name]

class SensorVariable(models.Model):
    sensor      = models.ForeignKey(Sensor)
    name        = models.CharField(max_length=255)
    unit        = models.CharField(max_length=50, blank=True, default='')
    max_const   = models.FloatField(null=True, blank=True)
    max_in_rrd  = models.BooleanField(default=False)
    is_rate     = models.BooleanField()

class Check(models.Model):
    sensor      = models.ForeignKey(Sensor)
    uuid        = models.CharField(max_length=40, blank=True, default='', editable=False, unique=True)
    exec_host   = models.ForeignKey(hosts.Host, related_name="check_exec_set")
    target_host = models.ForeignKey(hosts.Host, related_name="check_target_set")
    target_obj  = models.CharField(max_length=255, blank=True, default='') # e.g. /dev/sda, eth0 if necessary

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        return models.Model.save(self, *args, **kwargs)
