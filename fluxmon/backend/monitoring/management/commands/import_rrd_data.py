# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import logging

from datetime           import datetime, timedelta
from optparse           import make_option

from django.core.management.base        import BaseCommand
from django.utils.timezone              import make_aware, get_default_timezone
from django.db                          import transaction

from monitoring.models  import Check


class Command( BaseCommand ):
    help = "Import data for a source from RRDtool fetch output."
    option_list = BaseCommand.option_list + (
        make_option( "-m", "--metrics",
            help="Space-separated list of metrics to import (read from the first line if empty). Use - to skip metrics.",
            default=""
            ),
        make_option( "-c", "--check",
            help="Check UUID (mandatory).",
            default=None
            ),
        make_option( "-i", "--interval", default=300, type=int,
            help="Interval between values to be imported in seconds."
            ),
    )

    def handle(self, **options):
        if not options["check"]:
            logging.critical("The --check option is mandatory.")

        check = Check.objects.get(uuid=options["check"])
        metrics = [ check.sensor.sensorvariable_set.get(name=metric) for metric in options["metrics"].split() if metric != "-" ]

        reading_data = False
        last_ts = make_aware(datetime.fromtimestamp(0), get_default_timezone())

        start_ts = datetime.now()
        count = 0

        with transaction.atomic():
            while True:
                line = sys.stdin.readline().strip()

                if not line:
                    if not reading_data:
                        reading_data = True
                        continue
                    else:
                        break

                if not reading_data:
                    # headline
                    if not metrics:
                        metrics = [ check.sensor.sensorvariable_set.get(name=metric) for metric in line.split() ]

                if reading_data:
                    ts_str, v_str = line.split(": ")
                    timestamp = make_aware(datetime.fromtimestamp(int(ts_str)), get_default_timezone())
                    if timestamp - last_ts < timedelta(seconds=options["interval"]):
                        continue
                    last_ts = timestamp
                    values = [float(value) for value in v_str.split()]
                    for metric, value in zip(metrics, values):
                        if value != value: # value is NaN
                            continue
                        check.checkmeasurement_set.create(variable=metric, measured_at=timestamp, value=value)
                        count += 1

        finish_ts = datetime.now()
        logging.warning( "Imported %d datasets in %.2f seconds.", count, (finish_ts - start_ts).total_seconds() )
