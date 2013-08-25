# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes        import generic

class ItemDisplay(models.Model):
    content_type    = models.ForeignKey(ContentType)
    object_id       = models.PositiveIntegerField()
    content_object  = generic.GenericForeignKey('content_type', 'object_id')
    display         = models.CharField(max_length=250, blank=False, null=False)

    class Meta:
        unique_together = (('content_type', 'object_id'),)

    def __unicode__(self):
        return "%s (%s)" % (self.display, unicode(self.content_object))
