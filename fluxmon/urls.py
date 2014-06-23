# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/',     include(admin.site.urls)),
    #url(r'^accounts/',  include('registration.urls') ),

    url(r'^accounts/login/$',                              'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$',                             'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^hosts/$',                                       'hosts.views.domains'),
    url(r'^hosts/(?P<fqdn>[\w\.\-]+)$',                    'hosts.views.host'),
    url(r'^hosts/(?P<fqdn>[\w\.\-]+)/delete$',             'hosts.views.delete_host'),
    url(r'^hosts/(?P<domain>[\d]+)/add$',                 'hosts.views.add_host'),
    url(r'^accounts/profile/$',                            'monitoring.views.profile'),
    url(r'^search/$',                                      'monitoring.views.search'),
    url(r'^conf/(?P<host_fqdn>[\w\.\-]+)$',                'monitoring.views.config'),
    url(r'^display/(?P<app>\w+)/(?P<obj>\w+)',             'display.views.set_display'),
    url(r'^details/(?P<uuid>[\w\d-]+)/',                   'monitoring.views.check_details'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).html', 'monitoring.views.render_check_page'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+)/(?P<profile>[\d\w]+).html', 'monitoring.views.render_check_page'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).png',  'monitoring.views.render_check'),

    url(r'^/?$',                                          'django.views.generic.simple.direct_to_template', {'template': 'index.html'}),
)
