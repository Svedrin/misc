# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.template                import RequestContext
from django.http                    import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf   import csrf_exempt

from hosts.models import Host
from monitoring.models import Sensor, Check
from monitoring.graphbuilder import Graph

def config(request, host_fqdn):
    if not request.user.is_authenticated():
        return HttpResponseForbidden("unauthorized")

    hh = get_object_or_404(Host, fqdn=(host_fqdn + '.'))
    conf = [request.user.apikey_set.all()[0].config]
    conf.append(hh.config)
    conf.extend([s.config for s in Sensor.objects.all()])
    conf.extend([chk.config for chk in hh.check_exec_set.all()])
    return HttpResponse(''.join(conf).encode("utf-8"), mimetype="text/plain")

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
            added = True
        except Check.DoesNotExist:
            exec_host   = Host.objects.get(fqdn=params["node"])
            target_host = Host.objects.get(fqdn=params["target"])
            sensor      = Sensor.objects.get(name=params["sensor"])
            check = Check(uuid=params["uuid"], exec_host=exec_host, target_host=target_host, target_obj=params["obj"])
            check.save()
            added = False
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
            results.append({
                "uuid": result["uuid"],
                "errmessage": err,
                "success": False
            })
        else:
            if check.user_allowed(request.user):
                check.process_result(result)
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

    builder.add_source( check.rrd.get_source(ds) )

    return HttpResponse(builder.get_image(), mimetype="image/png")

