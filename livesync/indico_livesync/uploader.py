# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re

from indico.core.db import db
from indico.util.console import verbose_iterator
from indico.util.string import strip_control_chars

from indico_livesync.simplify import SimpleChange, process_records


class Uploader:
    """Handles batch data upload to a remote service."""

    def __init__(self, backend, verbose=False, from_cli=False):
        self.backend = backend
        self.verbose = verbose
        self.from_cli = from_cli
        self.logger = backend.plugin.logger

    def run(self, records):
        """Runs the batch upload

        :param records: an iterable containing queue entries
        """
        self_name = type(self).__name__
        simplified = process_records(records).items()
        total = len(simplified)
        if self.from_cli:
            simplified = self._make_verbose(simplified, total)
        try:
            self.logger.info(f'{self_name} uploading %d changes from %d records', total, len(records))
            self.upload_records(simplified)
        except Exception:
            self.logger.exception(f'{self_name} failed')
            if self.from_cli:
                raise
            return
        self.processed_records(records)
        self.logger.info(f'{self_name} finished (%d total changes from %d records)', total, len(records))

    def run_initial(self, records, total):
        """Runs the initial batch upload

        :param records: an iterable containing records
        :param total: the total of records to be exported
        :return: True if everything was successful, False if not
        """
        records = ((rec, SimpleChange.created) for rec in records)
        records = self._make_verbose(records, total)
        return self.upload_records(records, initial=True)

    def _make_verbose(self, iterator, total):
        return verbose_iterator(
            iterator,
            total,
            lambda entry: entry[0].id,
            lambda entry: re.sub(r'\s+', ' ', strip_control_chars(getattr(entry[0], 'title', ''))),
            print_total_time=True
        )

    def upload_records(self, records, initial=False):
        """Executed to upload records.

        :param records: an iterator of records to upload (or queue entries)
        :param initial: whether the upload is part of an initial export
        :return: True if everything was successful, False if not
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
