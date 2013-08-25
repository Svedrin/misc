# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django                 import template
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from django.conf            import settings

from display.models import ItemDisplay

register = template.Library()


@register.filter
def display( obj, field="name" ):
    """ Return the display content if set, else getattr(``obj``, ``field``). """
    content_type = ContentType.objects.get_for_model(obj)
    try:
        display = ItemDisplay.objects.get(content_type=content_type, object_id=obj.id)
    except ItemDisplay.DoesNotExist:
        # fallback to the old method (which utterly sucks balls and is soon to be removed)
        if hasattr(obj, "display") and obj.display:
            return obj.display
        return getattr(obj, field)
    else:
        return display.display

@register.filter
def displayonly( obj ):
    """ Return ``obj.display`` if set, else ''. """
    content_type = ContentType.objects.get_for_model(obj)
    try:
        display = ItemDisplay.objects.get(content_type=content_type, object_id=obj.id)
    except ItemDisplay.DoesNotExist:
        return ""
    else:
        return display.display

@register.filter
def displayform( obj, field="name" ):
    content_type = ContentType.objects.get_for_model(obj)
    return render_to_string( 'display/displayform.html',  {
        'display': display(obj, field),
        'app':     content_type.app_label,
        'model':   content_type.model,
        'obj':     obj,
        'placeholder': getattr(obj, field)
        } )
