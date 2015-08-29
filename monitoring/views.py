# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import re
import json
import operator

from datetime import datetime, timedelta
from time import time

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.template                import RequestContext
from django.http                    import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.core.serializers.json   import DjangoJSONEncoder
from django.views.decorators.csrf   import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views      import redirect_to_login
from django.db                      import transaction, ProgrammingError
from django.db.models               import Q
from django.core.urlresolvers       import reverse
from django.utils.timezone          import make_aware, get_default_timezone

from hosts.models import Host
from monitoring.models import Sensor, SensorVariable, Check, Alert, CheckViewcount, View
from monitoring.forms  import SearchForm
from monitoring.graphbuilder import Graph
from monitoring.graphunits   import parse, extract_units


@login_required
def config(request, host_fqdn):
    hh = get_object_or_404(Host, fqdn=host_fqdn)
    if not hh.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    conf = [request.user.publickey_set.get(host=hh).config]
    conf.append("node %s\n" % hh.fqdn)
    for target in Host.objects.filter( id__in=hh.check_exec_set.values("target_host").distinct() ).exclude(id=hh.id):
        conf.append("target %s\n" % target.fqdn)
    conf.extend([s.config for s in Sensor.objects.all()])
    conf.extend([chk.config for chk in hh.check_exec_set.all()])
    return HttpResponse(''.join(conf).encode("utf-8"), content_type="text/plain")


@login_required
def profile(request):
    most_viewed = request.user.checkviewcount_set.all().order_by("-count")[:5]
    return render_to_response("profile.html", {
        'searchform':  SearchForm(),
        'most_viewed': most_viewed,
        }, context_instance=RequestContext(request))


@login_required
def search(request):
    results = None

    if request.method == 'POST' or "query" in request.GET:
        if request.method == "POST":
            searchform = SearchForm(request.POST)
        else:
            searchform = SearchForm(request.GET)
        if searchform.is_valid():
            results = Check.objects.filter(is_active=True)
            host_kwds  = []
            check_kwds = []
            var_kwds   = []
            for keyword in searchform.cleaned_data["query"].split():
                if Host.objects.filter(fqdn__istartswith=keyword):
                    host_kwds.append(Q(fqdn__istartswith=keyword))
                elif SensorVariable.objects.filter(Q(name__istartswith=keyword) | Q(display__istartswith=keyword)):
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
            if results.count() == 1:
                if len(var_kwds) == 1:
                    try:
                        var = results[0].sensor.sensorvariable_set.get(Q(name__istartswith=var_kwds[0]) | Q(display__istartswith=var_kwds[0]))
                        return HttpResponseRedirect(reverse(render_check_page, args=(results[0].uuid, var.name)))
                    except (SensorVariable.DoesNotExist, SensorVariable.MultipleObjectsReturned):
                        pass
                return HttpResponseRedirect(reverse(check_details, args=(results[0].uuid,)))
            results = results.order_by('target_host__fqdn', 'exec_host__fqdn', 'sensor__name')
            #print results.query
    else:
        searchform = SearchForm()

    return render_to_response("monitoring/search.html", {
        'searchform':  searchform,
        'have_query':  results is not None,
        'list_checks': results,
        }, context_instance=RequestContext(request))


def check_details(request, uuid):
    check = get_object_or_404(Check, uuid=uuid)
    if not check.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    if check.sensor.sensorvariable_set.count() == 1:
        var = check.sensor.sensorvariable_set.all()[0]
        return HttpResponseRedirect(reverse(render_check_page, args=(check.uuid, var.name)))
    svars = []
    for variable in check.sensor.sensorvariable_set.order_by('name'):
        alerts = []
        if check.current_alert:
            alerts = check.current_alert.alertvariable_set.filter(variable=variable, fail=True)
        svars.append((variable, alerts))
    return render_to_response("monitoring/checkdetails.html", {
        'check': check,
        'vars':  svars,
        'views': View.objects.filter(variables__sensor__check=check).distinct(),
        }, context_instance=RequestContext(request))

def render_check_page(request, uuid, ds, profile="24h"):
    check = get_object_or_404(Check, uuid=uuid)
    if not check.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    return render_to_response("monitoring/graph.html", {
        'check':    check,
        'variable': check.sensor.sensorvariable_set.get(name=ds)
        }, context_instance=RequestContext(request))


def render_check(request, uuid, ds):
    check = Check.objects.get(uuid=uuid)
    if not check.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())

    builder = Graph()
    try:
        builder.start  = int(request.GET.get("start",  check.rrd.last_check - 24*60*60))
        builder.end    = int(request.GET.get("end",    check.rrd.last_check))
    except ValueError, err:
        print >> sys.stderr, unicode(err)
        raise Http404("Invalid start or end specified")

    builder.height = int(request.GET.get("height", 150))
    builder.width  = int(request.GET.get("width",  700))
    builder.bgcol  = request.GET.get("bgcol", "FFFFFF")
    builder.fgcol  = request.GET.get("fgcol", "000000")
    builder.grcol  = request.GET.get("grcol", "EEEEEE")
    builder.sacol  = request.GET.get("sacol", "")
    builder.sbcol  = request.GET.get("sbcol", "")
    builder.grad   = request.GET.get("grad", "false") == "true"
    builder.title  = unicode(check)

    rrd = check.rrd
    rrd.prediction = request.GET.get("prediction", "true") == "true"

    var = check.sensor.sensorvariable_set.get(name=ds)

    with transaction.atomic():
        lock_check = Check.objects.select_for_update().get(id=check.id)
        try:
            vc = check.checkviewcount_set.select_for_update().get(variable=var, user=request.user)
        except CheckViewcount.DoesNotExist:
            vc = check.checkviewcount_set.create(variable=var, user=request.user, count=1)
        else:
            vc.count += 1
            vc.save()

    if var.formula:
        srcline = var.formula
    else:
        srcline = var.name

    if var.unit:
        unit = var.unit
    else:
        unit = None

    for src in parse(srcline):
        node = src.get_value(rrd)
        builder.add_source( node )
        if unit is None:
            unit = unicode(extract_units(node))

    if unit is not None:
        builder.verttitle = unit

    return HttpResponse(builder.get_image(), content_type="image/png")

def get_check_data(request):
    check = Check.objects.get(uuid=request.GET["check"])
    if not check.has_perm(request.user, "r"):
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
            measurements = check.get_measurements(ds, start, end)
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
        logging.error(measurements.query.sql % tuple(["'%s'" % param for param in measurements.params]))
        raise

    response["data_window"] = {
        "start": min( metric["start"] for metric in response["metrics"].values() ),
        "end":   max( metric["end"]   for metric in response["metrics"].values() ),
    }

    response["query_time"] = end_time - start_time

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder), content_type="application/json")

def render_interactive_check_page(request, uuid, ds):
    check = get_object_or_404(Check, uuid=uuid)
    if not check.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    var = check.sensor.sensorvariable_set.get(name=ds)
    varinfo = [{
        "name": var.name,
        "display": var.display,
        "formula": var.formula,
        "unit": var.get_unit()
    }]
    return render_to_response("monitoring/interactive_graph.html", {
        'check':     check,
        'view':      None,
        'variable':  var,
        'variables': json.dumps(varinfo)
        }, context_instance=RequestContext(request))


def render_view_page(request, uuid, view_id):
    check = get_object_or_404(Check, uuid=uuid)
    view  = get_object_or_404(View,  id=view_id)
    if not check.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    varinfo = [{
        "name": var.name,
        "display": var.display,
        "formula": var.formula,
        "unit": var.get_unit()
    } for var in view.variables.all()]
    return render_to_response("monitoring/interactive_graph.html", {
        'check':     check,
        'view':      view,
        'variable':  view,
        'variables': json.dumps(varinfo)
        }, context_instance=RequestContext(request))

