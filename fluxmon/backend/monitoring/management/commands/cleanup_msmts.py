# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import datetime

from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, get_default_timezone

from monitoring.models import CheckMeasurement

class Command( BaseCommand ):
    help = "Delete measurements older than 90 days."

    def handle(self, **options):
        ninety_days_ago = make_aware(datetime.datetime.now() - datetime.timedelta(days=90), get_default_timezone())
        CheckMeasurement.objects.filter(measured_at__lt=ninety_days_ago).delete()
