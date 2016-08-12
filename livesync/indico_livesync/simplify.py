# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

import itertools
from collections import defaultdict

from sqlalchemy.orm import joinedload

from indico.core.db import db
from indico.modules.categories.models.categories import Category
from indico.modules.events.models.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution

from indico.util.struct.enum import IndicoEnum
from indico_livesync.models.queue import ChangeType, EntryType


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
    cascaded_records = set()

    for record in records:
        if record.change != ChangeType.deleted and record.object is None:
            # Skip entries which are not deletions but have no corresponding objects.
            # Probably they are updates for objects that got deleted afterwards.
            continue
        if record.change == ChangeType.created:
            assert record.type != EntryType.category
            changes[record.object] |= SimpleChange.created
        elif record.change == ChangeType.deleted:
            assert record.type != EntryType.category
            changes[record.object] |= SimpleChange.deleted
        elif record.change in {ChangeType.moved, ChangeType.protection_changed}:
            cascaded_records.add(record)
        elif record.change == ChangeType.data_changed:
            assert record.type != EntryType.category
            changes[record.object] |= SimpleChange.updated

    for obj in _process_cascaded(cascaded_records):
        changes[obj] |= SimpleChange.updated

    return changes


def _process_cascaded(records):
    category_prot_records = {rec.category_id for rec in records if rec.type == EntryType.category
                             and rec.change == ChangeType.protection_changed}
    category_move_records = {rec.category_id for rec in records if rec.type == EntryType.category
                             and rec.change == ChangeType.moved}

    event_records = {rec.event_id for rec in records if rec.type == EntryType.event}
    session_records = {rec.session_id for rec in records if rec.type == EntryType.session}
    contribution_records = {rec.contribution_id for rec in records if rec.type == EntryType.contribution}
    subcontribution_records = {rec.subcontribution_id for rec in records if rec.type == EntryType.subcontribution}

    changed_events = set()
    changed_contributions = set()
    changed_subcontributions = set()

    category_prot_records -= category_move_records  # A move already implies sending the whole record

    # Protection changes are handled differently, as there may not be the need to re-generate the record
    if category_prot_records:
        for categ in Category.find(Category.id.in_(category_prot_records)):
            cte = categ.get_protection_parent_cte()
            # Update only children that inherit
            inheriting_categ_children = (Event.query
                                         .join(cte, db.and_((Event.category_id == cte.c.id),
                                                            (cte.c.protection_parent == categ.id))))
            inheriting_direct_children = Event.find((Event.category_id == categ.id) & Event.is_inheriting)

            changed_events.update(itertools.chain(inheriting_direct_children, inheriting_categ_children))

    # Add move operations and explicitly-passed event records
    if category_move_records:
        changed_events.update(Event.find(Event.category_chain_overlaps(category_move_records)))
    if event_records:
        changed_events.update(Event.find(Event.id.in_(event_records)))

    for event in changed_events:
        yield event

    # Sessions are added (explicitly changed only, since they don't need to be sent anywhere)
    if session_records:
        changed_contributions.update(Contribution
                                     .find(Contribution.session_id.in_(session_records), ~Contribution.is_deleted))

    # Contributions are added (implictly + explicitly changed)
    changed_event_ids = {ev.id for ev in changed_events}

    condition = Contribution.event_id.in_(changed_event_ids) & ~Contribution.is_deleted
    if contribution_records:
        condition = db.or_(condition, Contribution.id.in_(contribution_records))
    contrib_query = Contribution.find(condition).options(joinedload('subcontributions'))

    for contribution in contrib_query:
        yield contribution
        changed_subcontributions.update(contribution.subcontributions)

    # Same for subcontributions
    if subcontribution_records:
        changed_subcontributions.update(SubContribution
                                        .find(SubContribution.contribution_id.in_(subcontribution_records)))
    for subcontrib in changed_subcontributions:
        yield subcontrib
