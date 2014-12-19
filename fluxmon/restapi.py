# kate: space-indent on; indent-width 4; replace-tabs on;

import logging

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets, permissions


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    #permission_classes = (IsNonAnonymous,)



def get_router():
    modules = []

    for app in settings.INSTALLED_APPS:
        try:
            module = __import__( app+".restapi" )
        except ImportError, err:
            if unicode(err) != "No module named restapi":
                logging.error("Got error when checking app %s: %s", app, unicode(err))
        else:
            modules.append(module)

    router = routers.DefaultRouter()
    router.register(r'users', UserViewSet)

    for module in modules:
        for (name, viewset) in getattr(getattr(module, "restapi"), "REST_API_VIEWSETS", []):
            router.register(name, viewset)

    return router

router = get_router()
