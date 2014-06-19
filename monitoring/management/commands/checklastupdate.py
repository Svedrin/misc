# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.core.urlresolvers    import reverse
from django.contrib.sites.models  import Site
from django.contrib.auth.models  import User
from django.utils.timezone       import make_aware, get_default_timezone
from django.template             import Template, Context

from hosts.models import Host


class Command( BaseCommand ):
    help = "Check last update timestamps for hosts and send notifications if necessary."

    def handle(self, **options):
        now = make_aware(datetime.now(), get_default_timezone())
        sv  = User.objects.get(username="Svedrin")

        template = Template("{{ host }} seems to be down "
            "(last updated {{ last_update|date:'SHORT_DATETIME_FORMAT' }})...")

        for host in Host.objects.all():
            last_update = host.get_last_update()
            if now - last_update >= timedelta(minutes=10) and \
               now - last_update  < timedelta(minutes=15):
                sv.pushovernetuser.notify(
                    template.render(Context(dict(
                        host=host,
                        last_update=last_update
                    ))),
                    url="http://%s%s" % (
                        Site.objects.get_current().domain,
                        reverse("hosts.views.host", args=(host.fqdn,))),
                    url_title="View host in Fluxmon"
                )
