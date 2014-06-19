# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.db import models
from django.contrib.auth import models as auth

from mptt.models import MPTTModel, TreeForeignKey

from fluxacl.models import ACL

class Domain(MPTTModel):
    name        = models.CharField(max_length=64)
    parent      = TreeForeignKey('self', null=True, blank=True, related_name='children')
    ownergroups = models.ManyToManyField(auth.Group, blank=True)
    subscribers = models.ManyToManyField(auth.User,  blank=True)
    acl         = models.ForeignKey(ACL, null=True, blank=True)

    class Meta:
        unique_together=( ('name', 'parent'), )

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        if not self.name:
            return ''
        return "%s.%s" % (self.name, unicode(self.parent) if self.parent is not None else '')

    def has_perm(self, user_or_role, flag, target_model=None):
        if user_or_role.is_superuser:
            return True
        if target_model is None:
            target_model = Domain
        if self.acl is not None:
            if self.acl.has_perm(user_or_role, flag, target_model):
                return True
        if self.parent is not None:
            return self.parent.has_perm(user_or_role, flag, target_model)
        return False

    @property
    def all_acls(self):
        if self.is_root_node():
            inh = []
        else:
            inh = self.parent.all_acls
        if self.acl:
            return inh + [(self, self.acl)]
        return inh

    def get_hosts(self):
        return self.host_set.order_by("fqdn")

class Host(models.Model):
    fqdn        = models.CharField(max_length=255, unique=True)
    domain      = TreeForeignKey(Domain)
    subscribers = models.ManyToManyField(auth.User, blank=True)
    acl         = models.ForeignKey(ACL, null=True, blank=True)
    last_update = models.DateTimeField(  null=True, blank=True)

    @property
    def config(self):
        return "node %s\n" % self.fqdn

    def __unicode__(self):
        return self.fqdn

    def get_last_update(self):
        """ Probe our checks' RRDs to determine the last time we received
            any updates, update last_update accordingly and return the
            value.
        """
        altered = False
        for check in self.check_target_set.filter(is_active=True):
            if self.last_update is None or check.last_update > self.last_update:
                self.last_update = check.last_update
                altered = True
        if altered:
            self.save()
        return self.last_update

    @property
    def all_acls(self):
        inh = self.domain.all_acls
        if self.acl:
            return inh + [(self, self.acl)]
        return inh

    def has_perm(self, user_or_role, flag, target_model=None):
        if user_or_role.is_superuser:
            return True
        if target_model is None:
            target_model = Host
        if self.acl is not None:
            if self.acl.has_perm(user_or_role, flag, target_model):
                return True
        return self.domain.has_perm(user_or_role, flag, target_model)
