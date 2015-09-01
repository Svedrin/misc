# kate: space-indent on; indent-width 4; replace-tabs on;

import logging

from django.conf import settings
from django.contrib.auth.models import User, Group

from rest_framework import routers, serializers, viewsets, permissions
from rest_framework.decorators import list_route
from rest_framework.response   import Response


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff', 'first_name', 'last_name', 'date_joined')

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    #permission_classes = (IsNonAnonymous,)

    @list_route()
    def self(self, request, *args, **kwargs):
        ser = UserSerializer(request.user, many=False, context={"request": request})
        return Response(ser.data)

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer



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
    router.register(r'users',  UserViewSet)
    router.register(r'groups', GroupViewSet)

    for module in modules:
        for args in getattr(getattr(module, "restapi"), "REST_API_VIEWSETS", []):
            router.register(*args)

    return router

router = get_router()
