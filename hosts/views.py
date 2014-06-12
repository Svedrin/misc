# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.http                    import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.template                import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers       import reverse

from hosts.models import Domain, Host
from hosts.forms  import ConfirmHostDeleteForm

@login_required
def domains(request):
    return render_to_response("hosts/domains.html", {
        'nodes': Domain.objects.all()
        }, context_instance=RequestContext(request))

def host(request, fqdn):
    thehost = get_object_or_404(Host, fqdn=fqdn)
    if not thehost.has_perm(request.user, "r"):
        return HttpResponseForbidden("Unauthorized")
    return render_to_response("hosts/host.html", {
        'host':   thehost,
        'checks': thehost.check_target_set.filter(is_active=True)
        }, context_instance=RequestContext(request))

def delete_host(request, fqdn):
    host = get_object_or_404(Host, fqdn=fqdn)
    if not thehost.has_perm(request.user, "d"):
        return HttpResponseForbidden("Unauthorized")
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

