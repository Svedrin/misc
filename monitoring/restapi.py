# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import django_filters

from datetime import datetime
from time import time

from django.contrib.auth.models import AnonymousUser
from django.shortcuts           import get_object_or_404
from django.utils.timezone      import make_aware, get_default_timezone
from django.http                import HttpResponse, HttpResponseForbidden
from django.db                  import ProgrammingError, DataError

from rest_framework import serializers, views, viewsets, status, authentication, permissions
from rest_framework.decorators import list_route, detail_route
from rest_framework.response   import Response
from rest_framework.filters    import BaseFilterBackend, DjangoFilterBackend

from hosts.models import Host, Domain

from monitoring.models import Sensor, SensorVariable, SensorParameter
from monitoring.models import Check,  CheckParameter
from monitoring.models import View
from monitoring.models import GraphAuthToken

class DomainSerializer(serializers.HyperlinkedModelSerializer):
    id          = serializers.Field()
    fqdn        = serializers.CharField()
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
    sensor  = serializers.CharField(source="sensor.name")
    unit    = serializers.CharField(source="get_unit")
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


class ViewSerializer(serializers.ModelSerializer):
    variables          = SensorVariableSerializer(many=True, read_only=True)
    class Meta:
        model = View

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
    views_set          = serializers.SerializerMethodField('get_views_set')

    def get_views_set(self, obj):
        ser = ViewSerializer(View.objects.filter(variables__sensor__check=obj).distinct(), many=True, read_only=True)
        return ser.data

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
    paginate_by      = 50
    lookup_field     = "uuid"

    @list_route()
    def most_viewed(self, request, *args, **kwargs):
        most_viewed = request.user.checkviewcount_set.all().order_by("-count")[:5]
        ser = CheckSerializer([cv.check_inst for cv in most_viewed], many=True, read_only=True, context={'request': request})
        return Response(ser.data)


def has_valid_token(request):
    header = authentication.get_authorization_header(request)
    if not header.lower().startswith("token "):
        return False
    _, token = header.split(" ", 1)
    try:
        GraphAuthToken.objects.get(token=token)
    except GraphAuthToken.DoesNotExist:
        return False
    else:
        return True

class GraphAuthTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if has_valid_token(request):
            anon = AnonymousUser()
            anon.username = authentication.get_authorization_header(request).split(" ", 1)[1]
            return (anon, None)
        return None

class HasValidGraphAuthToken(permissions.BasePermission):
    """ Require users to present a valid token. """

    def has_permission(self, request, view):
        if not request.user.is_anonymous():
            return True
        if request.method not in permissions.SAFE_METHODS:
            # not a read-only request -> no token auth
            return False
        return has_valid_token(request)

class GraphAuthTokenSerializer(serializers.ModelSerializer):
    check   = CheckSerializer(source="check_inst")
    variable = SensorVariableSerializer()
    view    = ViewSerializer()
    domain  = DomainSerializer()

    class Meta:
        model = GraphAuthToken

class GraphAuthTokenViewSet(viewsets.ViewSet):
    authentication_classes = (
        authentication.BasicAuthentication,
        authentication.SessionAuthentication,
        GraphAuthTokenAuthentication)
    permission_classes = (HasValidGraphAuthToken,)

    def create(self, request):
        token = GraphAuthToken()
        if "check" in request.DATA:
            token.check_inst = get_object_or_404(Check,  uuid=request.DATA["check"])
        if "domain" in request.DATA:
            token.domain     = get_object_or_404(Domain, id=request.DATA["domain"])
        if "variable" in request.DATA:
            sensorname, varname = request.DATA["variable"].split('.', 1)
            token.variable   = get_object_or_404(SensorVariable, sensor__name=sensorname, name=varname)
        if "view" in request.DATA:
            token.view       = get_object_or_404(View,   name=request.DATA["view"])
        token.full_clean()
        token.save()
        ser = GraphAuthTokenSerializer(token, context={"request": request})
        return Response(ser.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        token = get_object_or_404(GraphAuthToken, token=pk)
        ser = GraphAuthTokenSerializer(token, context={"request": request})
        return Response(ser.data)



class MeasurementsViewSet(viewsets.ViewSet):
    authentication_classes = (
        authentication.BasicAuthentication,
        authentication.SessionAuthentication,
        GraphAuthTokenAuthentication)
    permission_classes = (HasValidGraphAuthToken,)

    def list(self, request, format=None):
        check  = None
        domain = None
        token  = None
        variables = []

        if request.user.is_anonymous():
            token  = get_object_or_404(GraphAuthToken, token=request.user.username)
            check  = token.check_inst
            domain = token.domain
            if token.view is None:
                variables = [token.variable]
            else:
                variables = token.view.variables.all()
        elif request.GET.get("check", ""):
            check = get_object_or_404(Check, uuid=request.GET["check"])
        elif request.GET.get("domain", ""):
            domain = get_object_or_404(Domain, id=request.GET["domain"])
        else:
            return HttpResponseForbidden("I say nay nay")

        if not token:
            for ds in request.GET.getlist("variables"):
                if "." in ds:
                    sensorname, varname = ds.split('.', 1)
                    var = get_object_or_404(SensorVariable, sensor__name=sensorname, name=varname)
                    variables.append(var)
                elif check:
                    var = get_object_or_404(SensorVariable, sensor=check.sensor, name=ds)
                    variables.append(var)
                else:
                    return HttpResponseForbidden("I say nay nay")


        start  = make_aware(datetime.fromtimestamp(int(request.GET.get("start",  time() - 24*60*60))), get_default_timezone())
        end    = make_aware(datetime.fromtimestamp(int(request.GET.get("end",    time()))), get_default_timezone())

        response = {
            'request_window': {
                'start': start,
                'end':   end
            }
        }

        start_time = time()
        metrics = {}

        try:
            for var in variables:
                ds = "%s.%s" % (var.sensor.name, var.name)
                if check:
                    measurements = var.get_measurements(check, start, end)
                else:
                    measurements = var.get_aggregate_over(domain, "sum", start, end)

                metrics[ds] = {
                    "data": [(msmt.measured_at, msmt.value)
                        for msmt in measurements],
                    "start": None,
                    "end": None,
                    "resolution": measurements.resolution
                }

                if  metrics[ds]["data"]:
                    metrics[ds]["start"] = metrics[ds]["data"][ 0][0]
                    metrics[ds]["end"]   = metrics[ds]["data"][-1][0]

        except (ProgrammingError, DataError), err:
            import logging
            import traceback

            logging.error("Received exception when executing query")
            logging.error(measurements.query.sql, *["'%s'" % param for param in measurements.params])
            logging.error(traceback.format_exc())

            response["exception"] = {
                'str': unicode(err)
            }
            if request.user.is_superuser:
                response["exception"].update({
                    'traceback': traceback.format_exc(),
                    'query':     (measurements.query.sql % tuple(["'%s'" % param for param in measurements.params]))
                })
            response["type"] = "exception"

        else:
            response["data_window"] = {
                "start": min( metric["start"] for metric in metrics.values() ),
                "end":   max( metric["end"]   for metric in metrics.values() ),
            }
            response["metrics"] = metrics
            response["type"]    = "result"

        end_time = time()

        response["query_time"] = end_time - start_time

        return Response(response)




REST_API_VIEWSETS = [
    ('domains', DomainViewSet, 'domain'),
    ('hosts',   HostViewSet,   'host'),
    ('sensors', SensorViewSet, 'sensor'),
    ('checks',  CheckViewSet,  'check'),
    ('tokens',  GraphAuthTokenViewSet,  'token'),
    ('measurements',  MeasurementsViewSet,  'msmt'),
]
