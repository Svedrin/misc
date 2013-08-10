from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'fluxmon.views.home', name='home'),
    # url(r'^fluxmon/', include('fluxmon.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^conf/(?P<host_fqdn>[\w\.\-]+)$',               'monitoring.views.config'),
    url(r'^submit/?$',                                    'monitoring.views.process'),
    url(r'^render/(?P<uuid>[\w\d-]+)/(?P<ds>[\w_]+).png', 'monitoring.views.render_check'),
)
