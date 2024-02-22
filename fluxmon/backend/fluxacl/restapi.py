# kate: space-indent on; indent-width 4; replace-tabs on;

from django.contrib.contenttypes.models import ContentType
from rest_framework import routers, serializers, viewsets

from fluxacl.models import Role, ACL, Permit

class RoleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model  = Role
        fields = ('name', 'parent', 'user', 'valid_until')

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class ACLSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model  = ACL

class ACLViewSet(viewsets.ModelViewSet):
    queryset = ACL.objects.all()
    serializer_class = ACLSerializer

class PermitSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model  = Permit

class PermitViewSet(viewsets.ModelViewSet):
    queryset = Permit.objects.all()
    serializer_class = PermitSerializer

class ContentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model  = ContentType

class ContentTypeViewSet(viewsets.ModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer

REST_API_VIEWSETS = [
    ("roles", RoleViewSet),
    ("acls",  ACLViewSet),
    ("permits", PermitViewSet),
    ("contenttypes", ContentTypeViewSet),
    ]

