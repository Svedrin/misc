# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.contrib import admin

from msgsign.models import PublicKey

class PublicKeyAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'owner', 'description', 'active']

admin.site.register( PublicKey, PublicKeyAdmin )
