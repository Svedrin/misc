# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.contrib import admin

from monitoring.models import Sensor, SensorVariable, Check

class SensorVariableInline(admin.TabularInline):
    model = SensorVariable

class SensorAdmin(admin.ModelAdmin):
    inlines      = [SensorVariableInline]
    list_display = ['name']

class CheckAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'sensor', 'exec_host', 'target_host', 'target_obj', 'last_update']

admin.site.register( Sensor, SensorAdmin )
admin.site.register( Check,  CheckAdmin )
