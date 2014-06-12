# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from datetime import datetime

from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.contenttypes.models import ContentType

from mptt.models import MPTTModel, TreeForeignKey


class Role(MPTTModel):
    """ Some kind of group or user, either a logged-in Django user, or a Guest granted
        access via a sharing token.
    """
    name        = models.CharField(max_length=64, blank=True)
    parent      = TreeForeignKey('self', null=True, blank=True, related_name='children')
    user        = models.ForeignKey(User, blank=True, null=True)
    token       = models.CharField(max_length=37, blank=True)
    valid_until = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together=( ('name', 'parent'), )

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        if self.user:
            myname = self.user.username
        elif self.token:
            myname = "guest token %s" % self.token
        elif self.name:
            myname = self.name
        else:
            myname = "unnamed role"
        return "%s/%s" % (unicode(self.parent) if self.parent is not None else '', myname)

    def get_user(self):
        if self.user is not None:
            return self.user
        elif self.token:
            anon = AnonymousUser()
            anon.username = self.name
            anon.role_set = Role.objects.filter(token=self.token)
            return anon
        else:
            return ValueError("This role is not associated to a user")

    @property
    def is_user(self):
        return self.user is not None or self.token != ''

    @property
    def is_active(self):
        if self.user is not None:
            return self.user.is_active
        return self.valid_until is None or self.valid_until >= datetime.now()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return self.user is None

    @property
    def is_staff(self):
        if self.user is not None:
            return self.user.is_staff
        return False

    @property
    def is_superuser(self):
        if self.user is not None:
            return self.user.is_superuser
        return False

class ACL(models.Model):
    def has_perm(self, user_or_role, flag, target_model=None):
        if flag not in Permit.Flags:
            raise ValueError("invalid flag")

        if isinstance(user_or_role, User):
            for role in user_or_role.role_set.all():
                if self.has_perm(role, flag):
                    return True
            return False

        elif isinstance(user_or_role, Role):
            myperms = ""
            for node in list(user_or_role.get_ancestors()) + [user_or_role]:
                try:
                    if target_model is None:
                        permit = self.permit_set.get(role=node, target_type=None)
                    else:
                        permit = self.permit_set.get(role=node, target_type__in=(None,
                            ContentType.objects.get_for_model(target_model)
                            ))
                except Permit.DoesNotExist:
                    continue
                else:
                    add = True
                    print "Checking", permit
                    for permitflag in permit.privileges:
                        if permitflag == " ":
                            continue
                        elif permitflag == "+":
                            add = True
                        elif permitflag == "-":
                            add = False
                        else:
                            if add:
                                if permitflag not in myperms:
                                    myperms += permitflag
                            else:
                                myperms = myperms.replace(permitflag, "")

                    print myperms

            return "a" in myperms or flag in myperms

        else:
            raise ValueError("need instance of user or role, got %s instead" % type(user_or_role))


class Permit(models.Model):
    acl         = models.ForeignKey(ACL)
    role        = models.ForeignKey(Role)
    target_type = models.ForeignKey(ContentType, blank=True, null=True)
    privileges  = models.CharField(max_length=50)

    Flags = {
        "c": "create",
        "r": "read"  ,
        "u": "update",
        "d": "delete",
        "s": "share" ,
        "a": "admin" ,
    }

    def __unicode__(self):
        return "%s: %s" % (self.role, self.privileges)
