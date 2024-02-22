# kate: space-indent on; indent-width 4; replace-tabs on;

from django.conf import settings
from rest_framework import permissions


class IsNonAnonymous(permissions.BasePermission):
    """ Require users to be authenticated as a non-Anon user. """

    def has_permission(self, request, view):
        return request.user.is_authenticated() and \
               not request.user.is_anonymous() and \
               request.user.id != settings.ANONYMOUS_USER_ID


