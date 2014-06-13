# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import mock

from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser

from fluxacl.models import ACL, Role, Permit

class RoleTest(TestCase):
    def test_role_with_user(self):
        user = User(username="bigdaddy")
        role = Role(user=user)

        self.assertTrue(role.is_user)

        user.is_active = True
        self.assertTrue(role.is_active)
        user.is_active = False
        self.assertFalse(role.is_active)

        user.is_staff = True
        self.assertTrue(role.is_staff)
        user.is_staff = False
        self.assertFalse(role.is_staff)

        user.is_superuser = True
        self.assertTrue(role.is_superuser)
        user.is_superuser = False
        self.assertFalse(role.is_superuser)

        self.assertFalse(role.is_anonymous())
        self.assertEquals(role.get_user(), user)
        self.assertEquals(unicode(role), "/" + user.username)

    def test_role_with_token(self):
        token = "15d05027-1626-49c2-a6e3-e947336f65f8"
        role = Role(name="tokenrole", token=token)

        self.assertEquals(role.user, None)
        self.assertTrue(role.is_user)

        self.assertEquals(role.valid_until, None)
        self.assertTrue(role.is_active)
        self.assertTrue(role.get_user().is_active)

        role.valid_until = datetime.now() - timedelta(minutes=10)
        self.assertFalse(role.is_active)

        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertTrue(role.is_anonymous())

        user = role.get_user()
        self.assertIsInstance(user, AnonymousUser)
        self.assertEquals(user.username, "tokenrole")
        self.assertFalse(role.is_active)
        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertTrue(role.is_anonymous())
        self.assertTrue(role.is_authenticated())

        self.assertEquals(unicode(role), "/guest token %s" % token)

    def test_root_role(self):
        role = Role(name="root")
        self.assertEquals(role.user,  None)
        self.assertEquals(role.token, "")
        self.assertFalse(role.is_user)
        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertEquals(unicode(role), "/root")

    def test_root_descendant_role(self):
        root = Role(name="root")
        role = Role(name="descendant", parent=root)
        self.assertEquals(role.user,  None)
        self.assertEquals(role.token, "")
        self.assertFalse(role.is_user)
        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertEquals(unicode(role), "/root/descendant")
