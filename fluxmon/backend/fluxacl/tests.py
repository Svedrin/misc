# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser

from fluxacl.models import ACL, Role, Permit, TokenUser

class RoleTest(TestCase):
    """ Tests for the Role model. """

    def test_role_with_user(self):
        """ Test that a role associated to a user behaves correctly. """
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
        """ Test that a role associated to a token behaves correctly, especially
            that the TokenUser returned by the get_user method has sensible values.
        """
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
        """ Check that groups don't accidentally declare themselves users,
            staff or superusers.
        """
        role = Role(name="root")
        self.assertEquals(role.user,  None)
        self.assertEquals(role.token, "")
        self.assertFalse(role.is_user)
        with self.assertRaises(ValueError):
            role.get_user()
        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertEquals(unicode(role), "/root")

    def test_root_descendant_role(self):
        """ Same thing as test_root_role, but make sure it works for subgroups
            as well and they return their path correctly.
        """
        root = Role(name="root")
        role = Role(name="descendant", parent=root)
        self.assertEquals(role.user,  None)
        self.assertEquals(role.token, "")
        self.assertFalse(role.is_user)
        with self.assertRaises(ValueError):
            role.get_user()
        self.assertFalse(role.is_staff)
        self.assertFalse(role.is_superuser)
        self.assertEquals(unicode(role), "/root/descendant")


class ACLTest(TestCase):
    """ Tests for the ACL and Permit models. """

    def setUp(self):
        """ Set up a user, two roles (team and user) and an ACL. """
        self.user = User(username="bigdaddy")
        self.user.save()

        self.team = Role(name="bigteam")
        self.team.save()

        self.role = Role(user=self.user, parent=self.team)
        self.role.save()

        self.acl = ACL()
        self.acl.save()

    def tearDown(self):
        """ Delete our test stuff. """
        self.acl.delete()
        self.assertEquals(Permit.objects.all().count(), 0)
        self.role.delete()
        self.team.delete()
        self.user.delete()

    def test_empty_acl(self):
        """ Check that empty ACLs don't give any permissions. """
        self.assertFalse(self.acl.has_perm(self.user, "r"))

    def test_invalid_chars(self):
        """ Check that has_perm and add_perm don't accept bullshit flags. """
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, "+")
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, "-")
        with self.assertRaises(ValueError):
            self.acl.has_perm(self.user, " ")

        with self.assertRaises(ValueError):
            self.acl.add_perm(self.user, "+acr -r #")
        with self.assertRaises(ValueError):
            self.acl.add_perm(self.user, "")
        with self.assertRaises(ValueError):
            self.acl.add_perm(self.user, " ")
        with self.assertRaises(ValueError):
            self.acl.add_perm(self.user, "  + - ")

    def test_add_with_user_and_multiple_roles(self):
        """ Check that add_perm fails when the user posesses multiple roles. """
        role2 = Role(user=self.user, name="duplicate")
        role2.save()
        role3 = Role(user=self.user, name="triplicate")
        role3.save()
        try:
            with self.assertRaises(Role.MultipleObjectsReturned):
                self.acl.add_perm(self.user, "+a")
        finally:
            role2.delete()
            role3.delete()

    def test_add_with_non_user(self):
        """ Check that add_perm and has_perm fail when neither a user nor a role is passed. """
        with self.assertRaises(ValueError):
            self.acl.add_perm("gummybear", "+a")
        with self.assertRaises(ValueError):
            self.acl.has_perm("gummybear", "a")

    def test_simple_permission(self):
        """ Check that simple permission granting works and doesn't grant too much. """
        self.acl.add_perm(self.user, "+r")
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_multi_permission(self):
        """ Check that granting multiple permissions at once works without granting
            too much.
        """
        self.acl.add_perm(self.user, "+cruds")
        self.assertTrue( self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "u"))
        self.assertTrue( self.acl.has_perm(self.user, "d"))
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_admin_permission(self):
        """ Check that granting the admin permission is enough to grant everything. """
        self.acl.add_perm(self.user, "+a")
        self.assertTrue(self.acl.has_perm(self.user, "c"))
        self.assertTrue(self.acl.has_perm(self.user, "r"))
        self.assertTrue(self.acl.has_perm(self.user, "u"))
        self.assertTrue(self.acl.has_perm(self.user, "d"))
        self.assertTrue(self.acl.has_perm(self.user, "s"))
        self.assertTrue(self.acl.has_perm(self.user, "a"))

    def test_inherited_permission(self):
        """ Check that inherited permissions work. """
        self.acl.add_perm(self.team, "+c")
        self.assertFalse(self.acl.has_perm(self.team, "r"))
        self.assertTrue( self.acl.has_perm(self.team, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "c"))

    def test_simple_permission_negation(self):
        """ Check that we can revoke granted permissions. """
        self.acl.add_perm(self.user, "+rs -r")
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertFalse(self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "a"))

    def test_inherited_permission_negation(self):
        """ Check that we can revoke inherited permissions. """
        self.acl.add_perm(self.team, "+cruds")
        self.acl.add_perm(self.user, "-cud")
        self.assertTrue( self.acl.has_perm(self.user, "s"))
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertFalse(self.acl.has_perm(self.user, "u"))
        self.assertFalse(self.acl.has_perm(self.user, "d"))

    def test_simple_permission_with_target_type(self):
        """ Check that target_models are honoured correctly: Permissions
            granted without a type should be True regardless, those granted
            with a type should be True only when queried with that type (and
            none other).
        """
        self.acl.add_perm(self.user, "+r")
        self.acl.add_perm(self.user, "+c", target_model=User)
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=ACL))

    def test_simple_permission_revocation_with_target_type(self):
        """ Check that target_models are honoured correctly, even if one ACL
            contains two permits that grant a privilege to all except one
            certain target_model.
            For this test, it is critical that permits with target_model=None
            are evaluated before those with a target_model set, no matter
            the order in which they were inserted into the ACL.
        """
        self.acl.add_perm(self.user, "+r")
        self.acl.add_perm(self.user, "-r", target_model=User)
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "r", target_model=User))

        self.acl.add_perm(self.user, "-c", target_model=User)
        self.acl.add_perm(self.user, "+c")
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=User))

    def test_inherited_permission_with_target_type(self):
        """ Same thing as test_simple_permission_with_target_type, but this time
            we've inherited the permissions from our team.
        """
        self.acl.add_perm(self.team, "+r")
        self.acl.add_perm(self.team, "+c", target_model=User)
        self.assertTrue( self.acl.has_perm(self.user, "r"))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=User))
        self.assertTrue( self.acl.has_perm(self.user, "r", target_model=ACL))
        self.assertFalse(self.acl.has_perm(self.user, "c"))
        self.assertTrue( self.acl.has_perm(self.user, "c", target_model=User))
        self.assertFalse(self.acl.has_perm(self.user, "c", target_model=ACL))

    def test_negated_permission_with_target_type(self):
        """ To make our day complete, let's now modify our inherited
            permissions by adding +s and -c for the user.
        """
        self.acl.add_perm(self.team, "+crud")
        self.acl.add_perm(self.user, "+s", target_model=User)
        self.acl.add_perm(self.user, "-c", target_model=User)
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
