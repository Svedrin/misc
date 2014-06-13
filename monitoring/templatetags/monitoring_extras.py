# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django                 import template
from django.template.base   import Node, NodeList, TemplateSyntaxError
from django.template.loader import render_to_string
from django.conf            import settings

from display.models import ItemDisplay

register = template.Library()


class IfPermNode(Node):
    child_nodelists = ('nodelist_true', 'nodelist_false')

    def __init__(self, flag, target, nodelist_true, nodelist_false):
        self.flag   = flag
        self.target = target
        self.nodelist_true  = nodelist_true
        self.nodelist_false = nodelist_false

    def __repr__(self):
        return "<IfPermNode>"

    def render(self, context):
        flag   = self.flag.resolve(context, True)
        target = self.target.resolve(context, True)
        if hasattr(target, "has_perm") and target.has_perm(context["user"], flag):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)



@register.tag
def ifperm(parser, token):
    """ Outputs the contents of the block if we have a certain permission,
        and (optionally) the else block if we don't.

        Example::

            {% ifperm r on check %}
                We can see the check yaay!
            {% else %}
                We can't see the check :(
            {% endifperm %}
    """
    bits = list(token.split_contents())
    if len(bits) != 4 or bits[2] != 'on':
        raise TemplateSyntaxError("Usage: %s <permission> on <object>" % bits[0])
    end_tag = 'end' + bits[0]
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == "else":
        nodelist_false = parser.parse((end_tag, ))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    flag   = parser.compile_filter(bits[1])
    target = parser.compile_filter(bits[3])
    return IfPermNode(flag, target, nodelist_true, nodelist_false)
