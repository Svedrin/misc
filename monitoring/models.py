# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from datetime import datetime, timedelta

from django.db import models, transaction
from django.utils.timezone import make_aware, get_default_timezone, utc
from django.contrib.auth.models import User

from hosts import models as hosts
from sensors.sensor import SensorMeta
from fluxacl.models import ACL
from monitoring.rrd import RRD
from monitoring.graphsql import parse, SensorNamespace


def get_default_start_end(start, end):
    if start is None:
        start = make_aware(datetime.now() - timedelta(days=1), get_default_timezone())
    if end is None:
        end   = start + timedelta(days=1)
    return start, end


def get_resolution(start, end):
    dt = end - start
    resolutions = (
        ('minute', timedelta(minutes=5)),
        ('hour',   timedelta(hours=1)),
        ('day',    timedelta(days=1)),
        ('month',  timedelta(days=30)),
        ('year',   timedelta(days=365))
    )
    for res_name, res_dt in resolutions:
        data_res = res_name
        if dt.total_seconds() / res_dt.total_seconds() <= 250:
            break
    return data_res


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
    aggregate   = models.BooleanField("Offer aggregtion over domains",            default=False)
    formula     = models.CharField(   "Formula used to calculate this value",     max_length=255, default='', blank=True)

    class Meta:
        unique_together=( ('sensor', 'name'), )

    def __unicode__(self):
        return "%s: %s" % (self.sensor.name, self.name)

    def get_unit(self):
        if self.formula and not self.unit:
            return unicode( list(parse(self.formula))[0].get_unit(SensorNamespace(self.sensor)) )
        return self.unit

    def get_aggregate_over(self, domain, fn="sum", start=None, end=None):
        if fn not in ("sum", "avg"):
            raise ValueError("fn needs to be either sum or avg")
        start, end = get_default_start_end(start, end)
        #data_res   = get_resolution(start, end)
        data_res = 'minute'
        args   = [data_res, self.id, data_res]
        result = CheckMeasurement.objects.raw("""select
            min(x.id) as id, min(x.check_id) as check_id, min(x.variable_id) as variable_id,
            date_trunc(%s, x.measured_at) as measured_at,
            avg(x.value) as value
            from (
                select distinct
                    -1 as id,
                    NULL as check_id,
                    cm.variable_id,
                    date_trunc('minute', cm.measured_at) as measured_at,
                    """ + fn + """(cm.value) as value
                from
                    monitoring_checkmeasurement cm
                where
                    variable_id = %s
                group by
                    cm.variable_id,
                    date_trunc('minute', cm.measured_at)
                order by measured_at ) as x
            group by date_trunc(%s, x.measured_at);""", args)
        result.resolution = data_res
        return result


class View(models.Model):
    name        = models.CharField(   "Human-readable view name",  max_length=255)
    variables   = models.ManyToManyField(SensorVariable)

    def __unicode__(self):
        return self.name


class OutdatedChecksQuerySet(models.query.QuerySet):
    def __iter__(self):
        for check in models.query.QuerySet.__iter__(self):
            lu  = check.last_update
            now = make_aware(datetime.now(), get_default_timezone())
            if lu is None or (now - lu) > timedelta(minutes=5):
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
    acl         = models.ForeignKey(ACL, null=True, blank=True)

    objects     = CheckManager()

    def __unicode__(self):
        paramstring = self.paramstring
        if paramstring:
            paramstring = "(%s)" % paramstring
        return "%s%s @ %s" % (self.sensor.name,
            paramstring,
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
        if self.rrd.last_update is None:
            return None
        return make_aware(self.rrd.last_update, utc)

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

    @property
    def all_acls(self):
        inh = self.target_host.all_acls
        if self.acl:
            return inh + [(self, self.acl)]
        return inh

    def has_perm(self, user_or_role, flag, target_model=None):
        if user_or_role.is_superuser:
            return True
        if target_model is None:
            target_model = Check
        if self.acl is not None:
            if self.acl.has_perm(user_or_role, flag, target_model):
                return True
        return self.target_host.has_perm(user_or_role, flag, target_model)

    def user_allowed(self, user):
        return self.has_perm(user, "u")

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

            with transaction.atomic():
                timestamp = make_aware(datetime.fromtimestamp(int(result["timestamp"])), get_default_timezone())
                for key in result["data"]:
                    self.checkmeasurement_set.create(variable=self.sensor.sensorvariable_set.get(name=key),
                                                     measured_at=timestamp, value=result["data"][key])

            self.rrd.update(result)
            confintervals = self.rrd.get_confidence_intervals(result["data"].keys())
            curralert = self.current_alert
            if max([info["fail"] and not (info["lower"] <= result["data"][varname] <= info["upper"])
                    for varname, info in confintervals.items() ]):
                # if we have any failed values, update alerts
                if curralert is None:
                    curralert = Alert(check_inst=self, starttime=make_aware(datetime.now(), get_default_timezone()), endtime=None, failcount=0)
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

    def get_measurements(self, variable, start=None, end=None):
        var = self.sensor.sensorvariable_set.get(name=variable)

        start, end = get_default_start_end(start, end)
        data_res = get_resolution(start, end)
        #print "resolution is now", data_res

        if not var.formula:
            topnode = list(parse(var.name))[0]
        else:
            topnode = list(parse(var.formula))[0]

        args     = [variable, self.sensor.id]
        valuedef = topnode.get_value(args)
        args.extend([self.id, self.sensor.id, start, end, data_res])
        result = CheckMeasurement.objects.raw("""select
                -1 as id,
                cm.check_id,
                (select id from monitoring_sensorvariable where name=%s and sensor_id=%s) as variable_id,
                min(cm.measured_at) as measured_at,
                """ + valuedef + """ as value
            from
                monitoring_checkmeasurement cm
                inner join monitoring_sensorvariable sv on variable_id=sv.id
            where
                cm.check_id=%s and
                sv.sensor_id=%s and
                cm.measured_at BETWEEN %s AND %s
            group by
                cm.check_id,
                date_trunc(%s, cm.measured_at)
            order by measured_at ;""", args)
        result.resolution = data_res
        return result



def __check_pre_delete(instance, **kwargs):
    instance.rrd.delete()

models.signals.pre_delete.connect(__check_pre_delete, sender=Check)


class CheckParameter(models.Model):
    check_inst  = models.ForeignKey(Check, db_column="check_id")
    parameter   = models.ForeignKey(SensorParameter)
    value       = models.CharField("Parameter value", max_length=255)

    class Meta:
        unique_together = (("check_inst", "parameter"), )

    def __unicode__(self):
        return "%s.%s = %s" % (self.parameter.sensor.name, self.parameter.name, self.value)


class CheckViewcount(models.Model):
    check_inst  = models.ForeignKey(Check, db_column="check_id")
    variable    = models.ForeignKey(SensorVariable)
    user        = models.ForeignKey(User)
    count       = models.IntegerField(default=0)


class CheckMeasurement(models.Model):
    check_inst  = models.ForeignKey(Check, db_column="check_id")
    variable    = models.ForeignKey(SensorVariable)
    measured_at = models.DateTimeField()
    value       = models.FloatField()

    def __unicode__(self):
        return "%s:\t%.2f" % (self.measured_at, self.value)


class Alert(models.Model):
    check_inst  = models.ForeignKey(Check, db_column="check_id")
    starttime   = models.DateTimeField()
    endtime     = models.DateTimeField(null=True)
    failcount   = models.IntegerField()

    class Meta:
        get_latest_by = "starttime"


class AlertVariable(models.Model):
    alert       = models.ForeignKey(Alert)
    variable    = models.ForeignKey(SensorVariable)
    timestamp   = models.DateTimeField()
    fail        = models.BooleanField(default=False)
    exp_lower   = models.FloatField()
    exp_upper   = models.FloatField()
    value       = models.FloatField()

    def __unicode__(self):
        return unicode(self.variable)
