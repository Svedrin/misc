# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from datetime import datetime, timedelta

from django.db import models
from django.utils.timezone import make_aware, get_default_timezone

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
    formula     = models.CharField(   "Formula used to calculate this value",     max_length=255, default='', blank=True)

    class Meta:
        unique_together=( ('sensor', 'name'), )

    def __unicode__(self):
        return "%s: %s" % (self.sensor.name, self.name)


class OutdatedChecksQuerySet(models.query.QuerySet):
    def __iter__(self):
        for check in models.query.QuerySet.__iter__(self):
            lu = check.last_update
            if lu is None or (datetime.now() - lu) > timedelta(minutes=5):
                yield check
        raise StopIteration

    def count(self):
        return len(list(self))

class CheckManager(models.Manager):
    def get_outdated(self):
        return OutdatedChecksQuerySet(self.model, using=self._db)

class Check(models.Model):
    sensor      = models.ForeignKey(Sensor)
    uuid        = models.CharField("Check UUID", max_length=40, blank=True, default='', editable=False, unique=True)
    exec_host   = models.ForeignKey(hosts.Host, verbose_name="The host that executes the check", related_name="check_exec_set")
    target_host = models.ForeignKey(hosts.Host, verbose_name="The host that is being checked",   related_name="check_target_set")
    display     = models.CharField("Human-readable name", max_length=255, default='', blank=True)
    is_active   = models.BooleanField(default=True, blank=True)

    objects     = CheckManager()

    def __unicode__(self):
        return "%s(%s) @ %s" % (self.sensor.name,
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

    @property
    def current_alert(self):
        try:
            return self.alert_set.get(endtime=None)
        except Alert.DoesNotExist:
            return None

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

    def activate(self):
        if not self.is_active:
            self.is_active = True
            self.save()

    def deactivate(self):
        if self.is_active:
            self.is_active = False
            self.save()

    def process_result(self, result):
        if result["data"] is not None:
            self.activate()
            self.rrd.update(result)
            confintervals = self.rrd.get_confidence_intervals(result["data"].keys())
            curralert = self.current_alert
            if max([info["fail"] and not (info["lower"] <= result["data"][varname] <= info["upper"])
                    for varname, info in confintervals.items() ]):
                # if we have any failed values, update alerts
                if curralert is None:
                    curralert = Alert(check=self, starttime=make_aware(datetime.now(), get_default_timezone()), endtime=None, failcount=0)
                curralert.failcount += 1
                curralert.save()
                for varname, info in confintervals.items():
                    curralert.alertvariable_set.create(
                        variable  = self.sensor.sensorvariable_set.get(name=varname),
                        timestamp = make_aware(datetime.now(), get_default_timezone()),
                        fail      = info["fail"],
                        exp_lower = info["lower"],
                        exp_upper = info["upper"],
                        value     = result["data"][varname])
            else:
                if curralert is not None:
                    curralert.endtime = make_aware(datetime.now(), get_default_timezone())
                    curralert.save()

def __check_pre_delete(instance, **kwargs):
    instance.rrd.delete()

models.signals.pre_delete.connect(__check_pre_delete, sender=Check)


class CheckParameter(models.Model):
    check       = models.ForeignKey(Check)
    parameter   = models.ForeignKey(SensorParameter)
    value       = models.CharField("Parameter value", max_length=255)

    class Meta:
        unique_together = (("check", "parameter"), )

    def __unicode__(self):
        return "%s.%s = %s" % (self.parameter.sensor.name, self.parameter.name, self.value)


class Alert(models.Model):
    check       = models.ForeignKey(Check)
    starttime   = models.DateTimeField()
    endtime     = models.DateTimeField(null=True)
    failcount   = models.IntegerField()

    class Meta:
        get_latest_by = "starttime"


class AlertVariable(models.Model):
    alert       = models.ForeignKey(Alert)
    variable    = models.ForeignKey(SensorVariable)
    timestamp   = models.DateTimeField()
    fail        = models.BooleanField()
    exp_lower   = models.FloatField()
    exp_upper   = models.FloatField()
    value       = models.FloatField()

    def __unicode__(self):
        return unicode(self.variable)
