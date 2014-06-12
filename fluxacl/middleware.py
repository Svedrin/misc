# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.core.exceptions import ImproperlyConfigured

from fluxacl.models import Role

class TokenUserMiddleware(object):
    """ Middleware for using share tokens in order to view otherwise protected
        pages.
    """

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The share token middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the AnonymousUserMiddleware class.")
        # If the user is already authenticated, we don't need to continue.
        if request.user.is_authenticated() and not request.user.is_anonymous():
            return
        # Check if we have a token in request.GET and see if we can resolve it
        # to a valid role.
        if "token" in request.GET and request.GET["token"]:
            try:
                role = Role.objects.get(token=request.GET["token"])
            except Role.DoesNotExist:
                return
            if not role.is_active or not role.is_anonymous():
                return
            request.user = role.get_user()
