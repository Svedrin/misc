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
    url(r'^hosts/$',                                       'hosts.views.domains'),
    url(r'^domain/(?P<id>\d+)$',                           'hosts.views.domain'),
    url(r'^hosts/(?P<fqdn>[\w\.\-]+)$',                    'hosts.views.host'),
    url(r'^hosts/(?P<fqdn>[\w\.\-]+)/delete$',             'hosts.views.delete_host'),
    url(r'^hosts/(?P<domain>[\d]+)/add$',                  'hosts.views.add_host'),
    url(r'^accounts/profile/$',                            'monitoring.views.profile'),
    url(r'^search/$',                                      'monitoring.views.search'),
    url(r'^conf/(?P<host_fqdn>[\w\.\-]+)$',                'monitoring.views.config'),
    url(r'^display/(?P<app>\w+)/(?P<obj>\w+)',             'display.views.set_display'),
    url(r'^details/(?P<uuid>[\w\d-]+)/',                   'monitoring.views.check_details'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).html', 'monitoring.views.render_check_page'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).png',  'monitoring.views.render_check'),
    url(r'^check.json',                                    'monitoring.views.get_check_data'),
    url(r'^check/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).html',  'monitoring.views.render_interactive_check_page'),
    url(r'^view/(?P<uuid>[\w\d-]+)/(?P<view_id>\d+).html', 'monitoring.views.render_view_page'),

    url(r'^$',                                             TemplateView.as_view(template_name='index.html'), name="index.html"),

)
