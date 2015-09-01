# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import django_filters

from datetime import datetime
from time import time

from django.shortcuts           import get_object_or_404
from django.utils.timezone      import make_aware, get_default_timezone
from django.http                import HttpResponse, HttpResponseForbidden
from django.db                  import ProgrammingError

from rest_framework import serializers, views, viewsets, status
from rest_framework.decorators import list_route, detail_route
from rest_framework.response   import Response
from rest_framework.filters    import BaseFilterBackend, DjangoFilterBackend

from hosts.models import Host, Domain

from monitoring.models import Sensor, SensorVariable, SensorParameter
from monitoring.models import Check,  CheckParameter


class DomainSerializer(serializers.HyperlinkedModelSerializer):
    aggregates  = serializers.HyperlinkedIdentityField(view_name="domain-aggregates")

    class Meta:
        model = Domain

class DomainViewSet(viewsets.ModelViewSet):
    queryset         = Domain.objects.all()
    serializer_class = DomainSerializer

    @detail_route()
    def aggregates(self, request, *args, **kwargs):
        domain = self.get_object()
        aggrs = SensorVariable.objects.filter(aggregate=True, sensor__check__target_host__domain=domain).distinct()
        ser = SensorVariableSerializer(aggrs, many=True, read_only=True, context={'request': request})
        return Response(ser.data)

    @list_route()
    def tree(self, request, *args, **kwargs):
        stack   = []
        queryset = iter(Domain.objects.all())
        currdom = queryset.next()
        stack.append({
            'id':   currdom.id,
            'name': currdom.name,
            'fqdn': '',
            'children': []
        })

        while stack:
            # Get the next domain
            try:
                currdom = queryset.next()
            except StopIteration:
                break
            # serialize it
            hosts = HostSerializer(currdom.host_set.all().order_by('fqdn'), many=True, read_only=True, context={"request": request})
            res = {
                'id':   currdom.id,
                'name': currdom.name,
                'children': [],
                'hosts': hosts.data
            }
            # now find the node in the stack we need to attach the domain to
            if currdom.parent is not None:
                while stack[-1]["id"] != currdom.parent.id:
                    stack.pop()
            topdom = stack[-1]
            res["fqdn"] = "%s.%s" % (res["name"], topdom["fqdn"])
            topdom["children"].append(res)
            stack.append(res)

        return Response(stack[0])


class HostSerializer(serializers.HyperlinkedModelSerializer):
    id          = serializers.Field()
    config      = serializers.HyperlinkedIdentityField(view_name="host-config")

    class Meta:
        model = Host

class HostViewSet(viewsets.ModelViewSet):
    queryset         = Host.objects.all()
    serializer_class = HostSerializer

    @detail_route()
    def config(self, request, *args, **kwargs):
        hh = self.get_object()
        if not hh.has_perm(request.user, "r"):
            raise Exception("I say nay nay")
        conf = [request.user.publickey_set.get(host=hh).config]
        conf.append("node %s\n" % hh.fqdn)
        for target in Host.objects.filter( id__in=hh.check_exec_set.values("target_host").distinct() ).exclude(id=hh.id):
            conf.append("target %s\n" % target.fqdn)
        conf.extend([s.config for s in Sensor.objects.all()])
        conf.extend([chk.config for chk in hh.check_exec_set.all()])
        return HttpResponse(''.join(conf).encode("utf-8"), content_type="text/plain")



class SensorVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorVariable

class SensorParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorParameter

class SensorSerializer(serializers.HyperlinkedModelSerializer):
    sensorvariable_set  = SensorVariableSerializer(many=True, read_only=True)
    sensorparameter_set = SensorParameterSerializer(many=True, read_only=True)

    class Meta:
        model = Sensor

class SensorViewSet(viewsets.ModelViewSet):
    queryset         = Sensor.objects.all()
    serializer_class = SensorSerializer




class CheckParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source="parameter.name")
    class Meta:
        model = CheckParameter
        fields = ("parameter", "value")

class CheckSerializer(serializers.HyperlinkedModelSerializer):
    url                = serializers.HyperlinkedIdentityField(view_name="check-detail", lookup_field="uuid")
    sensor             = SensorSerializer()
    target_host        = HostSerializer()
    exec_host          = HostSerializer()
    checkparameter_set = CheckParameterSerializer(many=True, read_only=True)

    class Meta:
        model = Check

class CheckFilter(django_filters.FilterSet):
    target_host = django_filters.CharFilter(name="target_host__id", lookup_type="exact")
    exec_host   = django_filters.CharFilter(name="exec_host__id",   lookup_type="exact")
    sensor      = django_filters.CharFilter(name="sensor__name",    lookup_type="iexact")

    class Meta:
        model  = Check
        fields = ['target_host', 'exec_host', 'uuid', 'sensor', 'is_active']

class CheckSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        import operator
        from django.db.models import Q
        if "search" not in request.GET:
            return queryset
        results = queryset.filter(is_active=True)
        host_kwds  = []
        check_kwds = []
        var_kwds   = []
        for keyword in request.GET["search"].split():
            if Host.objects.filter(fqdn__icontains=keyword):
                host_kwds.append(Q(fqdn__icontains=keyword))
            elif SensorVariable.objects.filter(Q(name__icontains=keyword) | Q(display__icontains=keyword)):
                var_kwds.append(keyword)
            else:
                check_kwds.append(Q(uuid__icontains=keyword))
                check_kwds.append(Q(display__icontains=keyword))
                check_kwds.append(Q(checkparameter__value__icontains=keyword))
                check_kwds.append(Q(sensor__name__icontains=keyword))
        if check_kwds:
            results = results.filter(reduce(operator.or_, check_kwds))
        if var_kwds:
            results = results.filter(reduce(operator.or_, [
                Q(sensor__sensorvariable__name__istartswith=kw) for kw in var_kwds
            ] + [
                Q(sensor__sensorvariable__display__istartswith=kw) for kw in var_kwds
            ]))
        if host_kwds:
            hostqry = Host.objects.filter(reduce(operator.or_, host_kwds))
            results = results.filter(Q(exec_host__in=hostqry) | Q(target_host__in=hostqry))
        results = results.distinct()
        results = results.order_by('target_host__fqdn', 'exec_host__fqdn', 'sensor__name')
        return results

class CheckViewSet(viewsets.ModelViewSet):
    queryset         = Check.objects.all()
    serializer_class = CheckSerializer
    filter_backends  = (DjangoFilterBackend, CheckSearchFilter)
    filter_class     = CheckFilter
    paginate_by      = 10
    lookup_field     = "uuid"

    @list_route()
    def most_viewed(self, request, *args, **kwargs):
        most_viewed = request.user.checkviewcount_set.all().order_by("-count")[:5]
        ser = CheckSerializer([cv.check_inst for cv in most_viewed], many=True, read_only=True, context={'request': request})
        return Response(ser.data)


class MeasurementsViewSet(viewsets.ViewSet):
    def list(self, request, format=None):
        check = None
        domain = None
        if request.GET.get("check", ""):
            check = get_object_or_404(Check, uuid=request.GET["check"])
            if not check.has_perm(request.user, "r"):
                return HttpResponseForbidden("I say nay nay")
        elif request.GET.get("domain", ""):
            domain = get_object_or_404(Domain, id=request.GET["domain"])
            if not domain.has_perm(request.user, "r"):
                return HttpResponseForbidden("I say nay nay")
        else:
            return HttpResponseForbidden("I say nay nay")

        start  = make_aware(datetime.fromtimestamp(int(request.GET.get("start",  time() - 24*60*60))), get_default_timezone())
        end    = make_aware(datetime.fromtimestamp(int(request.GET.get("end",    time()))), get_default_timezone())

        response = {
            'request_window': {
                'start': start,
                'end':   end
            },
            'metrics': {}
        }

        try:
            start_time = time()

            for ds in request.GET.getlist("variables"):
                if "." in ds:
                    sensorname, varname = ds.split('.', 1)
                else:
                    sensorname = None
                    varname = ds

                if check:
                    measurements = check.get_measurements(varname, start, end)
                else:
                    var = get_object_or_404(SensorVariable, sensor__name=sensorname, name=varname, aggregate=True)
                    measurements = var.get_aggregate_over(domain, "sum", start, end)

                response["metrics"][ds] = {
                    "data": [(msmt.measured_at, msmt.value)
                        for msmt in measurements],
                    "start": None,
                    "end": None,
                    "resolution": measurements.resolution
                }

                if response["metrics"][ds]["data"]:
                    response["metrics"][ds]["start"] = response["metrics"][ds]["data"][ 0][0]
                    response["metrics"][ds]["end"]   = response["metrics"][ds]["data"][-1][0]

            end_time = time()

        except ProgrammingError:
            import logging
            logging.error("Received exception when executing query")
            logging.error(measurements.query.sql, *["'%s'" % param for param in measurements.params])
            raise

        response["data_window"] = {
            "start": min( metric["start"] for metric in response["metrics"].values() ),
            "end":   max( metric["end"]   for metric in response["metrics"].values() ),
        }

        response["query_time"] = end_time - start_time

        return Response(response)


REST_API_VIEWSETS = [
    ('domains', DomainViewSet, 'domain'),
    ('hosts',   HostViewSet,   'host'),
    ('sensors', SensorViewSet, 'sensor'),
    ('checks',  CheckViewSet,  'check'),
    ('measurements',  MeasurementsViewSet,  'msmt'),
]
