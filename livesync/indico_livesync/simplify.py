# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from collections import defaultdict

from indico.util.struct.enum import IndicoEnum

from indico_livesync.models.queue import ChangeType


class SimpleChange(int, IndicoEnum):
    deleted = 1
    created = 2
    updated = 4


def process_records(records):
    """Converts queue entries into object changes.

    :param records: an iterable containing `LiveSyncQueueEntry` objects
    :return: a dict mapping object references to `SimpleChange` bitsets
    """
    changes = defaultdict(int)

    for record in records:
        if record.change != ChangeType.deleted and record.object is None:
            # Skip entries which are not deletions but have no corresponding objects.
            # Probably they are updates for objects that got deleted afterwards.
            continue
        if record.change == ChangeType.created:
            if record.type != 'category':
                changes[record.object_ref] |= SimpleChange.created
        elif record.change == ChangeType.deleted:
            if record.type != 'category':
                changes[record.object_ref] = SimpleChange.deleted
        elif record.change in {ChangeType.moved, ChangeType.protection_changed}:
            for ref in _cascade(record):
                changes[ref] |= SimpleChange.updated
            changes.update()
        elif record.change == ChangeType.title_changed:
            pass  # XXX: included in data_changed
        elif record.change == ChangeType.data_changed:
            if record.type != 'category':
                changes[record.object_ref] |= SimpleChange.updated

    return changes


def _cascade(record):
    yield record.object_ref
    for subrecord in record.iter_subentries():
        if subrecord.object:
            for item in _cascade(subrecord):
                yield item
