# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
from datetime import date

from celery.schedules import crontab
from dateutil.relativedelta import relativedelta

from indico.core.celery import celery
from indico.core.config import config
from indico.core.storage.backend import ReadOnlyStorageMixin, get_storage

from indico_storage_s3.plugin import DynamicS3Storage


@celery.periodic_task(run_every=crontab(minute=0, hour=1))
def create_bucket():
    for key in config.STORAGE_BACKENDS:
        storage = get_storage(key)
        if not isinstance(storage, DynamicS3Storage) or isinstance(storage, ReadOnlyStorageMixin):
            continue
        today = date.today()
        placeholders = set(re.findall('<.*?>', storage.bucket_name_template))
        if not placeholders:
            continue
        elif placeholders == {'<year>', '<week>'}:
            bucket_date = today + relativedelta(weeks=1)
            bucket = storage._get_bucket_name(bucket_date)
            storage._create_bucket(bucket)
        elif placeholders == {'<year>', '<month>'} or placeholders == {'<year>'}:
            if '<month>' in placeholders or today.month == 12:
                bucket_date = today + relativedelta(months=1)
                bucket = storage._get_bucket_name(bucket_date)
                storage._create_bucket(bucket)
        else:
            raise RuntimeError('Invalid placeholder combination in bucket name template: {}'
                               .format(storage.bucket_name_template))
