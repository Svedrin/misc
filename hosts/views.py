# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import uuid

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.http                    import Http404, HttpResponse, HttpResponseRedirect
from django.template                import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views      import redirect_to_login
from django.core.urlresolvers       import reverse

from hosts.models import Domain, Host
from hosts.forms  import ConfirmHostDeleteForm, AddHostForm
from msgsign.models import PublicKey

@login_required
def domains(request):
    return render_to_response("hosts/domains.html", {
        'nodes': Domain.objects.all()
        }, context_instance=RequestContext(request))

def domain(request, id):
    domain = get_object_or_404(Domain, id=id)
    if not domain.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    from monitoring.models import SensorVariable
    return render_to_response("hosts/domain.html", {
        'domain': domain,
        'aggregates': SensorVariable.objects.filter(aggregate=True, sensor__check__target_host__domain=domain).distinct()
        }, context_instance=RequestContext(request))

def host(request, fqdn):
    thehost = get_object_or_404(Host, fqdn=fqdn)
    if not thehost.has_perm(request.user, "r"):
        return redirect_to_login(request.build_absolute_uri())
    return render_to_response("hosts/host.html", {
        'host':   thehost,
        'checks': thehost.check_target_set.filter(is_active=True)
        }, context_instance=RequestContext(request))

def delete_host(request, fqdn):
    host = get_object_or_404(Host, fqdn=fqdn)
    if not host.has_perm(request.user, "d"):
        return redirect_to_login(request.build_absolute_uri())
    if request.method == "POST":
        form = ConfirmHostDeleteForm( request.POST )
        if form.is_valid():
            if form.cleaned_data['fqdn'] == host.fqdn:
                host.check_target_set.all().delete()
                host.check_exec_set.all().delete()
                host.delete()
                return HttpResponseRedirect(reverse(domains))
    else:
        form = ConfirmHostDeleteForm()

    return render_to_response("hosts/hostdelete.html", {
        'host': host,
        'form': form,
        'target_checks': host.check_target_set.filter(is_active=True),
        'exec_checks':   host.check_exec_set.filter(is_active=True).exclude(target_host=host)
        }, context_instance=RequestContext(request))

@login_required
def add_host(request, domain):
    domain = get_object_or_404(Domain, id=domain)
    if not domain.has_perm(request.user, "c", target_model=Host):
        return redirect_to_login(request.build_absolute_uri())
    if request.method == "POST":
        postdata = request.POST.copy()
        if '.' not in postdata["fqdn"]:
            postdata["fqdn"] = "%s.%s" % (postdata["fqdn"], domain)
        if postdata["fqdn"][-1] != ".":
            postdata["fqdn"] += "."
        form = AddHostForm( postdata )
        if form.is_valid():
            thehost = Host.objects.create(fqdn=postdata["fqdn"], domain=domain)
            pubkey  = PublicKey.objects.create(
                        owner     = request.user,
                        host      = thehost,
                        uuid      = str(uuid.uuid4()),
                        publickey = postdata["pubkey"])
            return HttpResponseRedirect(reverse(host, args=(thehost.fqdn,)))
    else:
        form = AddHostForm()
        form.fields["fqdn"].help_text="hostname.%s" % domain

    return render_to_response("hosts/hostadd.html", {
        'domain': domain,
        'form': form,
        }, context_instance=RequestContext(request))
