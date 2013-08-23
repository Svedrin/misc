# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from monitoring.models import Check

@csrf_exempt
def set_display(request, app, obj):
    cc = Check.objects.get(id=request.POST["id"])
    cc.display = request.POST["display"]
    cc.save()
    return HttpResponse( json.dumps({"display": cc.display}), mimetype="application/json" )
