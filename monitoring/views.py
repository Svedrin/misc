# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import re
import json
import operator

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.template                import RequestContext
from django.http                    import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf   import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models               import Q
from django.core.urlresolvers       import reverse

from hosts.models import Host
from monitoring.models import Sensor, SensorVariable, Check
from monitoring.forms  import SearchForm
from monitoring.graphbuilder import Graph
from monitoring.graphunits   import parse, extract_units


@login_required
def config(request, host_fqdn):
    hh = get_object_or_404(Host, fqdn=(host_fqdn + '.'))
    conf = [request.user.apikey_set.all()[0].config]
    conf.append("node %s\n" % hh.fqdn)
    for target in Host.objects.filter( id__in=hh.check_exec_set.values("target_host").distinct() ).exclude(id=hh.id):
        conf.append("target %s\n" % target.fqdn)
    conf.extend([s.config for s in Sensor.objects.all()])
    conf.extend([chk.config for chk in hh.check_exec_set.all()])
    return HttpResponse(''.join(conf).encode("utf-8"), mimetype="text/plain")


@login_required
def profile(request):
    return render_to_response("profile.html", {
        'outdatedchecks': Check.objects.get_outdated(),
        'searchform': SearchForm()
        }, context_instance=RequestContext(request))


@login_required
def search(request):
    results = None

    if request.method == 'POST':
        searchform = SearchForm(request.POST)
        if searchform.is_valid():
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
                results = Check.objects.filter(reduce(operator.or_, check_kwds))
            else:
                results = Check.objects.all()
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


@login_required
def check_details(request, uuid):
    check = get_object_or_404(Check, uuid=uuid)
    if check.sensor.sensorvariable_set.count() == 1:
        var = check.sensor.sensorvariable_set.all()[0]
        return HttpResponseRedirect(reverse(render_check_page, args=(check.uuid, var.name)))
    return render_to_response("monitoring/checkdetails.html", {
        'check': check
        }, context_instance=RequestContext(request))

@login_required
def render_check_page(request, uuid, ds):
    check = get_object_or_404(Check, uuid=uuid)
    return render_to_response("monitoring/graph.html", {
        'check':    check,
        'variable': check.sensor.sensorvariable_set.get(name=ds)
        }, context_instance=RequestContext(request))

@csrf_exempt
def add_checks(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden("unauthorized")

    try:
        data = json.loads( request.raw_post_data )
    except ValueError, err:
        return HttpResponseBadRequest(err)

    if not isinstance(data, list):
        data = [data]

    results = []

    for params in data:
        try:
            check = Check.objects.get(uuid=params["uuid"])
            added = False
        except Check.DoesNotExist:
            exec_host   = Host.objects.get(fqdn=params["node"])
            target_host = Host.objects.get(fqdn=params["target"])
            sensor      = Sensor.objects.get(name=params["sensor"])
            check = Check(uuid=params["uuid"], sensor=sensor, exec_host=exec_host, target_host=target_host)
            check.save()
            for sensorparam in check.sensor.sensorparameter_set.all():
                if sensorparam.name in params:
                    check.checkparameter_set.create(parameter=sensorparam, value=params[sensorparam.name])
            added = True
        results.append({"added": added, "uuid": check.uuid})

    return HttpResponse(json.dumps(results, indent=2), mimetype="application/json")


@csrf_exempt
def process(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden("unauthorized")

    try:
        data = json.loads( request.raw_post_data )
    except ValueError, err:
        return HttpResponseBadRequest(err)

    if not isinstance(data, list):
        data = [data]

    results = []

    for result in data:
        if "check" not in result:
            results.append({
                "uuid": result["uuid"],
                "errmessage": "check uuid missing",
                "success": False
            })
        try:
            check = Check.objects.get(uuid=result["check"])
        except Check.DoesNotExist, err:
            print "Check %s does not exist" % result["uuid"]
            results.append({
                "uuid": result["uuid"],
                "errmessage": unicode(err),
                "success": False
            })
        else:
            if check.user_allowed(request.user):
                try:
                    check.process_result(result)
                except Exception, err:
                    import traceback
                    traceback.print_exc()
                    results.append({
                        "uuid": result["uuid"],
                        "errmessage": unicode(err),
                        "success": False
                    })
                else:
                    results.append({
                        "uuid": result["uuid"],
                        "success": True
                    })
            else:
                results.append({
                    "uuid": result["uuid"],
                    "errmessage": "permission denied",
                    "success": False
                })

    return HttpResponse(json.dumps(results, indent=2), mimetype="application/json")


@login_required
def render_check(request, uuid, ds):
    check = Check.objects.get(uuid=uuid)

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

    var = check.sensor.sensorvariable_set.get(name=ds)
    if var.formula:
        srcline = var.formula
    else:
        srcline = var.name

    if var.unit:
        unit = var.unit
    else:
        unit = None

    for src in parse(srcline):
        node = src.get_value(check.rrd)
        builder.add_source( node )
        if unit is None:
            unit = unicode(extract_units(node))

    if unit is not None:
        builder.verttitle = unit

    return HttpResponse(builder.get_image(), mimetype="image/png")

