# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.contrib import admin

from hosts.models import Domain, Host

class DomainAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']

class HostAdmin(admin.ModelAdmin):
    list_display = ['fqdn', 'domain']


admin.site.register( Domain, DomainAdmin )
admin.site.register( Host,   HostAdmin )
