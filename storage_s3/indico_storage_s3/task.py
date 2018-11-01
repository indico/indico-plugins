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

import re
from datetime import date

from celery.schedules import crontab
from dateutil.relativedelta import relativedelta

from indico.core.celery import celery
from indico.core.config import config
from indico.core.storage.backend import get_storage

from plugin import S3Storage


@celery.periodic_task(run_every=crontab(minute=0, hour=1))
def create_bucket():
    for key in config.STORAGE_BACKENDS:
        storage = get_storage(key)
        if not isinstance(storage, S3Storage):
            continue
        today = date.today()
        bucket_name = storage._get_original_bucket_name()
        placeholders = set(re.findall('<.*?>', bucket_name))
        if placeholders == {'<year>', '<week>'}:
            bucket_date = today + relativedelta(weeks=1)
            bucket = storage._replace_bucket_placeholders(bucket_name, bucket_date)
            storage._create_bucket(bucket)
        elif placeholders == {'<year>', '<month>'} or (placeholders == {'<year>'} and today.month == 12):
            bucket_date = today + relativedelta(months=1)
            bucket = storage._replace_bucket_placeholders(bucket_name, bucket_date)
            storage._create_bucket(bucket)
        elif placeholders == {'<month>'} or placeholders == {'<week>'} or placeholders == {'<month>', '<week>'}:
            raise RuntimeError('Placeholders combination in bucket name is not correct: %s', bucket_name)
