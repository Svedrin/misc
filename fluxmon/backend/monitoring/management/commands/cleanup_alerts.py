# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import datetime

from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, get_default_timezone

from monitoring.models import Alert

class Command( BaseCommand ):
    help = "Delete alerts older than a month."
    option_list = BaseCommand.option_list + (
        make_option( "-q", "--quiet",
            help="Don't log to stdout.",
            default=False, action="store_true"
            ),
    )

    def handle(self, **options):
        one_month_ago = make_aware(datetime.datetime.now() - datetime.timedelta(days=30), get_default_timezone())
        alertqry = Alert.objects.filter(endtime__isnull=False, endtime__lt=one_month_ago)
        if not options["quiet"]:
            print "Deleting %d alerts..." % alertqry.count()
        alertqry.delete()
