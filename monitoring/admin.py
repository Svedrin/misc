# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.contrib import admin

from monitoring.models import Sensor, SensorParameter, SensorVariable, Check, CheckParameter

class SensorParameterInline(admin.TabularInline):
    model = SensorParameter

class SensorVariableInline(admin.TabularInline):
    model = SensorVariable

class SensorAdmin(admin.ModelAdmin):
    inlines      = [SensorParameterInline, SensorVariableInline]
    list_display = ['name']

class CheckParameterInline(admin.TabularInline):
    model = CheckParameter

class CheckAdmin(admin.ModelAdmin):
    inlines      = [CheckParameterInline]
    list_display = ['uuid', 'sensor', 'exec_host', 'target_host', 'last_update']

admin.site.register( Sensor, SensorAdmin )
admin.site.register( Check,  CheckAdmin )
