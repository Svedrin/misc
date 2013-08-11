# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django import forms

from monitoring.models import Sensor, SensorVariable, Check

class SearchForm(forms.Form):
    query = forms.CharField()
