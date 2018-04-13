# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import datetime

from celery.schedules import crontab
from dateutil.relativedelta import relativedelta

from indico.core.celery import celery
from indico.core.storage.backend import get_storage


@celery.periodic_task(run_every=crontab(minute=0, hour=1))
def create_bucket():
    storage = get_storage('s3')
    bucket_name = storage.get_bucket_name(replace_placeholders=False)
    now = datetime.now()
    if all(x in bucket_name for x in ['<year>', '<week>']) and now.weekday() == 0:
        date = now + relativedelta(weeks=1)
        storage.create_bucket(storage.replace_bucket_placeholders(bucket_name, date))
    elif ((all(x in bucket_name for x in ['<year>', '<month>']) and now.day == 1)
          or ('<year>' in bucket_name and not any(x in bucket_name for x in ['<month>', '<week>'])
              and now.day == 1 and now.month == 12)):
        date = now + relativedelta(months=1)
        storage.create_bucket(storage.replace_bucket_placeholders(bucket_name, date))
