# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from datetime import datetime

from django.db import models
from django.utils.timezone import is_naive, make_aware, get_current_timezone
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.contenttypes.models import ContentType

from mptt.models import MPTTModel, TreeForeignKey


class TokenUser(AnonymousUser):
    """ Subclass of d.c.auth.models.AnonymousUser that returns True for
        is_authenticated.
    """
    def is_authenticated(self):
        return True


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
        """ Return the user this role is associated to (if any).

            Raises ValueError if this is not a user role. (See is_user.)
        """
        if self.user is not None:
            return self.user
        elif self.token:
            anon = TokenUser()
            anon.username  = self.name
            anon.is_active = self.is_active
            anon.role_set  = Role.objects.filter(token=self.token)
            return anon
        else:
            raise ValueError("This role is not associated to a user")

    @property
    def is_user(self):
        """ True if this is a user role. """
        return self.user is not None or self.token != ''

    @property
    def is_active(self):
        """ True if this is an active role. """
        if self.user is not None:
            return self.user.is_active
        if self.valid_until is None:
            return True
        expires = self.valid_until
        if is_naive(expires):
            expires = make_aware(expires, get_current_timezone())
        return expires >= make_aware(datetime.now(), get_current_timezone())

    def is_authenticated(self):
        """ For compatibility with Django's User model. Always returns True. """
        return True

    def is_anonymous(self):
        """ For compatibility with Django's User model. True if this role is
            associated to a Django database user, False for groups and tokens.
        """
        return self.user is None

    @property
    def is_staff(self):
        """ For compatibility with Django's User model. True if this role is
            associated to a Django database user who is a staff member, False
            otherwise.
        """
        return self.user is not None and self.user.is_staff

    @property
    def is_superuser(self):
        """ For compatibility with Django's User model. True if this role is
            associated to a Django database user who is a superuser, False
            otherwise.
        """
        return self.user is not None and self.user.is_superuser


class ACL(models.Model):
    """ An Access Control List.

        Features methods for building, managing and querying ACLs.
    """

    def get_perms(self, role, target_model=None):
        """ Get a list of effective permissions for a role and, optionally,
            a target_model.

            If target_model is given, permits concerning this certain model
            are also evaluated, resulting in more fine-grained access control.

            This method traverses the role's ancestors, evaluating the permits
            for each of them, lastly evaluates the role's very own permits,
            and returns the result.
        """
        myperms = []
        for node in list(role.get_ancestors()) + [role]:
            for permit in self.permit_set.filter(role=node).order_by("-target_type"):
                if permit.target_type is not None:
                    if target_model is None or \
                       permit.target_type != ContentType.objects.get_for_model(target_model):
                        continue
                add = True
                #print "Checking", permit
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
                                myperms.append(permitflag)
                        else:
                            if permitflag in myperms:
                                myperms.remove(permitflag)
                #print myperms
        return myperms

    def has_perm(self, user_or_role, flag, target_model=None):
        """ Check whether or not the given user or role has the given
            permission, optionally taking the target_model into account.
        """
        if flag not in Permit.Flags:
            raise ValueError("invalid flag")

        if isinstance(user_or_role, (User, AnonymousUser)):
            if hasattr(user_or_role, "role_set"):
                for role in user_or_role.role_set.all():
                    if self.has_perm(role, flag, target_model):
                        return True
            return False

        elif isinstance(user_or_role, Role):
            myperms = self.get_perms(user_or_role, target_model)
            return "a" in myperms or flag in myperms

        else:
            raise ValueError("need instance of user or role, got %s instead" % type(user_or_role))

    def add_perm(self, user_or_role, privileges, target_model=None):
        """ Add a permit for the given user or role, granting or revoking the
            given privileges, optionally taking the target_model into account.

            If passing a user, that user cannot be Anonymous and has to be
            associated to *exactly* one role. In other cases, pass a role.
        """
        if not privileges.replace("+", "").replace("-", "").strip():
            raise ValueError("privilege string doesn't modify any privileges: " + privileges)

        for char in privileges:
            if char not in ["+", "-", " "] + Permit.Flags.keys():
                raise ValueError("invalid flag: %s" % char)

        if isinstance(user_or_role, User):
            roles = user_or_role.role_set.all()
            if len(roles) != 1:
                raise Role.MultipleObjectsReturned("if passing a user, that user needs to be associated to exactly one role (got %d)" % len(roles))
            self.add_perm(roles[0], privileges, target_model)

        elif isinstance(user_or_role, Role):
            target_type = None
            if target_model is not None:
                target_type = ContentType.objects.get_for_model(target_model)
            self.permit_set.create(role=user_or_role, privileges=privileges, target_type=target_type)

        else:
            raise ValueError("need instance of user or role, got %s instead" % type(user_or_role))


class Permit(models.Model):
    """ An Access Control List entry, either granting or revoking a certain
        privilege, optionally for certain models only.

        If target_type is omitted, this permit will be valid for all models.

        Privileges is a string that adheres the following format:

            [+<flags>] [-<flags>]

        Flags preceded by + are granted, those preceded by - are revoked.
        Whitespace is ignored, so feel free to keep this readable.
    """
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
