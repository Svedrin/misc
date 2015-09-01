# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib import admin

from fluxmon.restapi import router

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/',     include(admin.site.urls)),
    #url(r'^accounts/',  include('registration.urls') ),

    url(r'^api/',      include(router.urls)),
    #url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    url(r'^accounts/login/$',                              'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$',                             'django.contrib.auth.views.logout', {'next_page': '/'}),

    url(r'^$',                                             TemplateView.as_view(template_name='index.html'), name="index.html"),

)
