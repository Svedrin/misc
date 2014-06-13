# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, AnonymousUser

from fluxacl.models import ACL, Role, Permit, TokenUser

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

        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertTrue(role.is_anonymous())
        self.assertTrue(role.is_authenticated())

        user = role.get_user()
        self.assertIsInstance(user, AnonymousUser)
        self.assertIsInstance(user, TokenUser)
        self.assertEquals(user.username, "tokenrole")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_anonymous())
        self.assertTrue(user.is_authenticated())

        role.valid_until = datetime.now() - timedelta(minutes=10)
        self.assertFalse(role.is_active)
        self.assertFalse(role.get_user().is_active)

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


class ACLTest(TestCase):
    def setUp(self):
        self.user = User(username="bigdaddy")
        self.user.save()

        self.team = Role(name="bigteam")
        self.team.save()

        self.role = Role(user=self.user, parent=self.team)
        self.role.save()

        self.acl = ACL()
        self.acl.save()

    def tearDown(self):
        self.acl.delete()
        self.assertEquals(Permit.objects.all().count(), 0)
        self.role.delete()
        self.team.delete()
        self.user.delete()

    def test_empty_acl(self):
        self.assertFalse(self.acl.has_perm(self.user, "r"))

    def test_invalid_chars(self):
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, "+")
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, "-")
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, " ")

    def test_simple_permission(self):
        self.acl.permit_set.create(role=self.role, privileges="+r")
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_multi_permission(self):
        self.acl.permit_set.create(role=self.role, privileges="+cruds")
        self.assertTrue( self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "u"))
        self.assertTrue( self.acl.has_perm(self.user, "d"))
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_admin_permission(self):
        self.acl.permit_set.create(role=self.role, privileges="+a")
        self.assertTrue(self.acl.has_perm(self.user, "c"))
        self.assertTrue(self.acl.has_perm(self.user, "r"))
        self.assertTrue(self.acl.has_perm(self.user, "u"))
        self.assertTrue(self.acl.has_perm(self.user, "d"))
        self.assertTrue(self.acl.has_perm(self.user, "s"))
        self.assertTrue(self.acl.has_perm(self.user, "a"))

    def test_inherited_permission(self):
        self.acl.permit_set.create(role=self.team, privileges="+c")
        self.assertFalse(self.acl.has_perm(self.team, "r"))
        self.assertTrue( self.acl.has_perm(self.team, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "c"))

    def test_simple_permission_negation(self):
        self.acl.permit_set.create(role=self.role, privileges="+rs -r")
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertFalse(self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_inherited_permission_negation(self):
        self.acl.permit_set.create(role=self.team, privileges="+cruds")
        self.acl.permit_set.create(role=self.role, privileges="-cud")
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "u"))
        self.assertFalse(self.acl.has_perm(self.user, "d"))

    def test_simple_permission_with_target_type(self):
        self.acl.permit_set.create(role=self.role, privileges="+r")
        self.acl.permit_set.create(role=self.role, privileges="+c",
                            target_type=ContentType.objects.get_for_model(User))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=ACL))

    def test_inherited_permission_with_target_type(self):
        self.acl.permit_set.create(role=self.team, privileges="+r")
        self.acl.permit_set.create(role=self.team, privileges="+c",
                            target_type=ContentType.objects.get_for_model(User))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=ACL))

    def test_negated_permission_with_target_type(self):
        self.acl.permit_set.create(role=self.team, privileges="+crud")
        self.acl.permit_set.create(role=self.role, privileges="+s",
                            target_type=ContentType.objects.get_for_model(User))
        self.acl.permit_set.create(role=self.role, privileges="-c",
                            target_type=ContentType.objects.get_for_model(User))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertTrue( self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.team, "c", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "s"))
        self.assertFalse(self.acl.has_perm(self.team, "s", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "s", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "s", target_model=ACL))
