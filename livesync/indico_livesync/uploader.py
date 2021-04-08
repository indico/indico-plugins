# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
from operator import attrgetter

from indico.core.db import db
from indico.util.console import verbose_iterator
from indico.util.iterables import grouper
from indico.util.string import strip_control_chars

from indico_livesync.simplify import process_records


class Uploader:
    """Handles batch data upload to a remote service."""

    #: Number of queue entries to process at a time
    BATCH_SIZE = 100
    #: Number of events to process at a time during initial export
    INITIAL_BATCH_SIZE = 500

    def __init__(self, backend):
        self.backend = backend
        self.logger = backend.plugin.logger

    def run(self, records):
        """Runs the batch upload

        :param records: an iterable containing queue entries
        """
        self_name = type(self).__name__
        for i, batch in enumerate(grouper(records, self.BATCH_SIZE, skip_missing=True), 1):
            self.logger.info('%s processing batch %d', self_name, i)
            try:
                for j, proc_batch in enumerate(grouper(
                        process_records(batch).items(), self.BATCH_SIZE, skip_missing=True), 1):
                    self.logger.info('%s uploading chunk #%d (batch %d)', self_name, j, i)
                    self.upload_records({k: v for k, v in proc_batch}, from_queue=True)
            except Exception:
                self.logger.exception('%s could not upload batch', self_name)
                return
            self.logger.info('%s finished batch %d', self_name, i)
            self.processed_records(batch)
        self.logger.info('%s finished', self_name)

    def run_initial(self, records, total, progress=True):
        """Runs the initial batch upload

        :param records: an iterable containing records
        :param total: the total of records to be exported
        :param progress: enable verbose progress mode
        """
        if progress:
            records = verbose_iterator(records, total, attrgetter('id'),
                                       lambda obj: re.sub(r'\s+', ' ', strip_control_chars(getattr(obj, 'title', ''))),
                                       print_total_time=True)
        for batch in grouper(records, self.INITIAL_BATCH_SIZE, skip_missing=True):
            self.upload_records(batch, from_queue=False)

    def upload_records(self, records, from_queue):
        """Executed for a batch of up to `BATCH_SIZE` records

        :param records: records to upload (queue entries or events)
        :param from_queue: if `records` contains queue entries.
                           expect events if it is False.
        """
        raise NotImplementedError  # pragma: no cover

    def processed_records(self, records):
        """Executed after successfully uploading a batch of records from the queue.

        :param records: a list of queue entries
        """
        for record in records:
            self.logger.debug('Marking as processed: %s', record)
            record.processed = True
        db.session.commit()
