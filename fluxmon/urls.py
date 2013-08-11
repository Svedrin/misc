from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/',     include(admin.site.urls)),
    #url(r'^accounts/',  include('registration.urls') ),

    url(r'^accounts/login/$',                             'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$',                            'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^accounts/profile/$',                           'monitoring.views.profile'),
    url(r'^search/$',                                     'monitoring.views.search'),
    url(r'^conf/(?P<host_fqdn>[\w\.\-]+)$',               'monitoring.views.config'),
    url(r'^submit/checks/$',                              'monitoring.views.add_checks'),
    url(r'^submit/results/$',                             'monitoring.views.process'),
    url(r'^details/(?P<uuid>[\w\d-]+)/',                  'monitoring.views.check_details'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).png', 'monitoring.views.render_check'),

    url(r'^/?$',                                          'django.views.generic.simple.direct_to_template', {'template': 'index.html'}),
)
