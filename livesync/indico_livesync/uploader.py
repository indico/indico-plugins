# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re

from indico.core.db import db
from indico.util.console import verbose_iterator
from indico.util.iterables import grouper
from indico.util.string import strip_control_chars

from indico_livesync.simplify import SimpleChange, process_records


class Uploader:
    """Handles batch data upload to a remote service."""

    #: Number of queue entries to process at a time
    BATCH_SIZE = 100

    def __init__(self, backend, verbose=False):
        self.backend = backend
        self.verbose = verbose
        self.logger = backend.plugin.logger

    def run(self, records):
        """Runs the batch upload

        :param records: an iterable containing queue entries
        """
        self_name = type(self).__name__
        simplified = process_records(records).items()
        chunks = list(grouper(simplified, self.BATCH_SIZE, skip_missing=True))
        try:
            for i, batch in enumerate(chunks, 1):
                self.logger.info(f'{self_name} uploading chunk %d/%d', i, len(chunks))
                self.upload_records(batch)
        except Exception:
            self.logger.exception(f'{self_name} could not upload batch')
            return
        self.processed_records(records)
        self.logger.info(f'{self_name} finished (%d total changes from %d records)', len(simplified), len(records))

    def run_initial(self, records, total):
        """Runs the initial batch upload

        :param records: an iterable containing records
        :param total: the total of records to be exported
        """
        records = verbose_iterator(
            ((rec, SimpleChange.created) for rec in records),
            total,
            lambda entry: entry[0].id,
            lambda entry: re.sub(r'\s+', ' ', strip_control_chars(getattr(entry[0], 'title', ''))),
            print_total_time=True
        )
        self.upload_records(records)

    def upload_records(self, records):
        """Executed for a batch of up to `BATCH_SIZE` records

        :param records: an iterator of records to upload (or queue entries)
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
