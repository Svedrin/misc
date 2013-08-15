# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from django.db import models

from hosts import models as hosts
from sensors.sensor import SensorMeta
from monitoring.rrd import RRD

class Sensor(models.Model):
    name        = models.CharField("Unique sensor name", max_length=255, unique=True)

    @property
    def sensor(self):
        return SensorMeta.sensortypes[self.name]

    @property
    def config(self):
        return "sensor %s\n" % self.name

    def __unicode__(self):
        return self.name


class SensorParameter(models.Model):
    sensor      = models.ForeignKey(Sensor)
    name        = models.CharField(   "Variable name as expected by the sensor",  max_length=255)
    type        = models.CharField(   "Data type",                                max_length=255, default='string', choices=(
        ("string",  "String"),
        ("int",     "Integer"),
        ("decimal", "Float")))
    display     = models.CharField(   "Human-readable name",                      max_length=255, default='', blank=True)
    help_text   = models.CharField(   "Help text",                                max_length=255, default='', blank=True)
    required    = models.BooleanField(default=True)
    default     = models.CharField(   "Default value",                            max_length=255, default='', blank=True)

    class Meta:
        unique_together=( ('sensor', 'name'), )

    def __unicode__(self):
        return "%s: %s" % (self.sensor.name, self.name)


class SensorVariable(models.Model):
    sensor      = models.ForeignKey(Sensor)
    name        = models.CharField(   "Variable name as returned by the sensor",  max_length=255)
    display     = models.CharField(   "Human-readable name",                      max_length=255, default='', blank=True)
    unit        = models.CharField(   "Unit",                                     max_length=50, blank=True, default='')
    max_const   = models.FloatField(  "Global constant maximum, if available",    null=True, blank=True)
    max_in_rrd  = models.BooleanField("Maximum is measured by the sensor",        default=False)
    is_rate     = models.BooleanField("Describes a rate of something per second", default=False)
    scale_by_2  = models.BooleanField("Scale by 1024 (Default: 1000)",            default=False)

    class Meta:
        unique_together=( ('sensor', 'name'), )

    def __unicode__(self):
        return "%s: %s" % (self.sensor.name, self.name)


class Check(models.Model):
    sensor      = models.ForeignKey(Sensor)
    uuid        = models.CharField("Check UUID", max_length=40, blank=True, default='', editable=False, unique=True)
    exec_host   = models.ForeignKey(hosts.Host, verbose_name="The host that executes the check", related_name="check_exec_set")
    target_host = models.ForeignKey(hosts.Host, verbose_name="The host that is being checked",   related_name="check_target_set")
    display     = models.CharField("Human-readable name", max_length=255, default='', blank=True)

    def __unicode__(self):
        return "%s(%s) %s" % (self.sensor.name,
            self.paramstring,
            self.target_host.fqdn[:-1])

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        return models.Model.save(self, *args, **kwargs)

    @property
    def paramstring(self):
        return ' '.join(["%s=%s" % (cp.parameter.name, cp.value) for cp in self.checkparameter_set.all()])

    @property
    def last_update(self):
        return self.rrd.last_update

    @property
    def config(self):
        return "check %s uuid=%s sensor=%s node=%s target=%s %s\n" % (
            self.display.replace(" ", "_") if self.display else self.uuid,
            self.uuid,
            self.sensor.name,
            self.exec_host.fqdn,
            self.target_host.fqdn,
            self.paramstring)

    @property
    def rrd(self):
        return RRD(self)

    def user_allowed(self, user):
        if user.is_superuser:
            return True
        domain = self.target_host.domain
        while domain is not None:
            for group in domain.ownergroups:
                if user in group.user_set.all():
                    return True
            domain = domain.parent
        return False

    def process_result(self, result):
        if result["data"] is not None:
            self.rrd.update(result)


class CheckParameter(models.Model):
    check       = models.ForeignKey(Check)
    parameter   = models.ForeignKey(SensorParameter)
    value       = models.CharField("Parameter value", max_length=255)

    class Meta:
        unique_together = (("check", "parameter"), )
