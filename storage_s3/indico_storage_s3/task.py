from __future__ import unicode_literals

import datetime

from celery.schedules import crontab
from dateutil.relativedelta import relativedelta

from indico.core.celery import celery
from indico.core.storage.backend import get_storage


@celery.periodic_task(run_every=crontab(minute=0, hour=1))
def create_bucket():
    storage = get_storage('s3')
    bucket_name = storage.get_bucket_name(replace_placeholders=False)
    now = datetime.datetime.now()
    if all(x in bucket_name for x in ['year', 'month', 'week']) and now.weekday() == 1:
        date = now + relativedelta(weeks=1)
        storage.create_bucket(storage.replace_bucket_placeholders(bucket_name, date))
    elif (all(x in bucket_name for x in ['year', 'month']) and now.day == 1
          or bucket_name.find('year') and now.day == 1 and now.month == 12):
        date = now + relativedelta(months=1)
        storage.create_bucket(storage.replace_bucket_placeholders(bucket_name, date))
