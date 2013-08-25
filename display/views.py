# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from monitoring.models import Check
from display.models    import ItemDisplay

@csrf_exempt
@login_required
def set_display(request, app, obj):
    content_type = ContentType.objects.get(app_label=app, model=obj)

    # TODO: use ItemDisplay.objects.update_or_create()
    display, created = ItemDisplay.objects.get_or_create(
        content_type = content_type,
        object_id    = int(request.POST["id"]),
        defaults     = {"display": request.POST["display"]}
        )
    if not created:
        display.display = request.POST["display"]
        display.save()

    # make sure the old field is cleared (will be removed soon)
    if hasattr(display.content_object, "display"):
        display.content_object.display = ''
        display.content_object.save()

    return HttpResponse( json.dumps({"display": display.display}), mimetype="application/json" )
