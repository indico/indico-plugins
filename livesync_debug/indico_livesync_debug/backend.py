# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import collections
from pprint import pformat

from pygments import highlight
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.lexers.agile import Python3Lexer

from indico.modules.search.schemas import (AttachmentSchema, ContributionSchema, EventNoteSchema, EventSchema,
                                           SubContributionSchema)
from indico.util.console import cformat

from indico_livesync import LiveSyncBackendBase, SimpleChange, Uploader, process_records


lexer = Python3Lexer()
formatter = Terminal256Formatter(style='native')


def _change_str(change):
    return ','.join(flag.name for flag in SimpleChange if change & flag)


def _print_record(obj_type, obj_id, data, changes, *, print_blank, verbose):
    if print_blank:
        print()  # verbose_iterator doesn't end its line
    print(f'{_change_str(changes)}: {obj_type} {obj_id}')
    if data is not None and verbose:
        print(highlight(pformat(data), lexer, formatter))
    return data


class DebugUploader(Uploader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_queue_run = False
        self.schemas = [
            EventSchema(exclude=('category_path',)),
            ContributionSchema(exclude=('category_path',)),
            SubContributionSchema(exclude=('category_path',)),
            AttachmentSchema(exclude=('category_path',)),
            EventNoteSchema(exclude=('category_path',)),
        ]

    def dump_record(self, obj):
        for schema in self.schemas:
            if isinstance(obj, schema.Meta.model):
                return schema.dump(obj)
        raise ValueError(f'unknown object ref: {obj}')

    def upload_records(self, records, initial=False):
        dumped_records = (
            (
                type(rec).__name__, rec.id,
                self.dump_record(rec) if not change_type & SimpleChange.deleted else None,
                change_type
            ) for rec, change_type in records
        )

        dumped_records = (_print_record(*x, print_blank=(not self._is_queue_run), verbose=self.verbose)
                          for x in dumped_records)
        collections.deque(dumped_records, maxlen=0)  # exhaust the iterator
        return True


class LiveSyncDebugBackend(LiveSyncBackendBase):
    """Debug

    This backend simply dumps all changes to stdout or the logger.
    """

    uploader = DebugUploader

    def process_queue(self, uploader, allowed_categories=()):
        records = self.fetch_records(allowed_categories)
        if not records:
            print(cformat('%{yellow!}No records%{reset}'))
            return

        print(cformat('%{white!}Raw changes:%{reset}'))
        for record in records:
            print(record)

        print()
        print(cformat('%{white!}Simplified/cascaded changes:%{reset}'))
        for obj, change in process_records(records).items():
            print(cformat('%{white!}{}%{reset}: {}').format(_change_str(change), obj))

        print()
        print(cformat('%{white!}Resulting records:%{reset}'))
        uploader._is_queue_run = True
        uploader.run(records)
        self.update_last_run()
