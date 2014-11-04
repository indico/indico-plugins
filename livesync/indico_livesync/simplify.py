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

from indico_livesync.models.queue import ChangeType


def process_records(records):
    changes = {}

    for record in records:
        if record.type != ChangeType.deleted and record.object is None:
            continue
        if record.type == ChangeType.created:
            changes[record.obj] = ChangeType.type
        elif record.type == ChangeType.deleted:
            changes[record.obj] = ChangeType.type
        elif record.type in {ChangeType.moved, ChangeType.protection_changed}:
            changes.update(_cascade_change(record))
        elif record.type == ChangeType.title_changed:
            pass
        elif record.type == ChangeType.data_changed and not record.category_id:
            changes[record.obj] = ChangeType.type

    for obj, state in records.iteritems():
        pass


def _cascade_change(record):
    changes = {record.obj: record.type}
    for subrecord in record.subrecords():
        changes.update(_cascade_change(subrecord))
    return changes
