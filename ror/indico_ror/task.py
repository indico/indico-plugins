# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2026 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from celery.schedules import crontab

from indico.core.celery import celery

from indico_ror.plugin import do_ror_sync, get_ror_csv, parse_csv


@celery.periodic_task(name='sync_ror', run_every=crontab(minute=0))
def sync_ror():
    csv = get_ror_csv()
    csv_dict = parse_csv(csv)
    do_ror_sync(csv_dict, False, False, 512)
