# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django                 import template
from django.template.loader import render_to_string

from django.conf            import settings

register = template.Library()


@register.filter
def display( obj, field="name" ):
    """ Display ``obj.display`` if set, else getattr(``obj``, ``field``). """
    if hasattr(obj, "display") and obj.display:
        return obj.display
    else:
        return getattr(obj, field)
