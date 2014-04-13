# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.shortcuts               import render_to_response, get_object_or_404, get_list_or_404
from django.template                import RequestContext
from django.contrib.auth.decorators import login_required

from hosts.models import Domain, Host

@login_required
def domains(request):
    return render_to_response("hosts/domains.html", {
        'nodes': Domain.objects.all()
        }, context_instance=RequestContext(request))

@login_required
def host(request, fqdn):
    thehost = get_object_or_404(Host, fqdn=fqdn)
    return render_to_response("hosts/host.html", {
        'host':   thehost,
        'checks': thehost.check_target_set.filter(is_active=True)
        }, context_instance=RequestContext(request))

