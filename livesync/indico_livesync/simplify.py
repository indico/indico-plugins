# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
from collections import defaultdict

from sqlalchemy.orm import joinedload

from indico.core.db import db
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.modules.categories.models.categories import Category
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.events import Event
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.events.sessions import Session
from indico.util.enum import IndicoEnum

from indico_livesync.models.queue import ChangeType, EntryType


class SimpleChange(int, IndicoEnum):
    deleted = 1
    created = 2
    updated = 4


CREATED_DELETED = SimpleChange.created | SimpleChange.deleted


def process_records(records):
    """Converts queue entries into object changes.

    :param records: an iterable containing `LiveSyncQueueEntry` objects
    :return: a dict mapping object references to `SimpleChange` bitsets
    """
    changes = defaultdict(int)
    cascaded_create_records = set()
    cascaded_update_records = set()
    cascaded_delete_records = set()
    cascaded_location_changes = set()

    for record in records:
        if record.change != ChangeType.deleted and record.object is None:
            # Skip entries which are not deletions but have no corresponding objects.
            # Probably they are updates for objects that got deleted afterwards.
            continue
        if record.change == ChangeType.created:
            assert record.type != EntryType.category
            cascaded_create_records.add(record)
        elif record.change == ChangeType.deleted:
            assert record.type != EntryType.category
            cascaded_delete_records.add(record)
        elif record.change in {ChangeType.moved, ChangeType.protection_changed}:
            cascaded_update_records.add(record)
        elif record.change == ChangeType.data_changed:
            assert record.type != EntryType.category
            changes[record.object] |= SimpleChange.updated
            # subcontributions have their parent's time information, so we need to
            # cascade contribution updates to them
            if record.type == EntryType.contribution:
                for subcontrib in record.object.subcontributions:
                    changes[subcontrib] |= SimpleChange.updated
        elif record.change == ChangeType.location_changed:
            assert record.type in (EntryType.event, EntryType.contribution, EntryType.session)
            cascaded_location_changes.add(record)

    for obj in _process_cascaded_category_contents(cascaded_update_records):
        changes[obj] |= SimpleChange.updated

    for obj in _process_cascaded_event_contents(cascaded_delete_records):
        changes[obj] |= SimpleChange.deleted

    for obj in _process_cascaded_event_contents(cascaded_create_records):
        changes[obj] |= SimpleChange.created

    for obj in _process_cascaded_locations(cascaded_location_changes):
        changes[obj] |= SimpleChange.updated

    created_and_deleted = {obj for obj, flags in changes.items() if (flags & CREATED_DELETED) == CREATED_DELETED}
    for obj in created_and_deleted:
        # discard any change where the object was both created and deleted
        del changes[obj]

    return changes


def _process_cascaded_category_contents(records):
    """
    Travel from categories to subcontributions, flattening the whole event structure.

    Yields everything that it finds (except for elements whose protection has changed
    but are not inheriting their protection settings from anywhere).

    :param records: queue records to process
    """
    category_prot_records = {rec.category_id for rec in records if rec.type == EntryType.category
                             and rec.change == ChangeType.protection_changed}
    category_move_records = {rec.category_id for rec in records if rec.type == EntryType.category
                             and rec.change == ChangeType.moved}

    changed_events = set()

    category_prot_records -= category_move_records  # A move already implies sending the whole record

    # Protection changes are handled differently, as there may not be the need to re-generate the record
    if category_prot_records:
        for categ in Category.query.filter(Category.id.in_(category_prot_records)):
            cte = categ.get_protection_parent_cte()
            # Update only children that inherit
            inheriting_categ_children = (Event.query
                                         .join(cte, db.and_((Event.category_id == cte.c.id),
                                                            (cte.c.protection_parent == categ.id))))
            inheriting_direct_children = Event.query.filter((Event.category_id == categ.id) & Event.is_inheriting)

            changed_events.update(itertools.chain(inheriting_direct_children, inheriting_categ_children))

    # Add move operations and explicitly-passed event records
    if category_move_records:
        changed_events.update(Event.query.filter(Event.category_chain_overlaps(category_move_records)))

    yield from _process_cascaded_event_contents(records, additional_events=changed_events)


def _process_cascaded_event_contents(records, additional_events=None):
    """
    Flatten a series of records into its most basic elements (subcontribution level).

    Yields results.

    :param records: queue records to process
    :param additional_events: events whose content will be included in addition to those
                              found in records
    """
    changed_events = additional_events or set()
    changed_sessions = set()
    changed_contributions = set()
    changed_subcontributions = set()
    changed_attachments = set()
    changed_notes = set()

    note_records = {rec.note_id for rec in records if rec.type == EntryType.note}
    attachment_records = {rec.attachment_id for rec in records if rec.type == EntryType.attachment}
    session_records = {rec.session_id for rec in records if rec.type == EntryType.session}
    contribution_records = {rec.contrib_id for rec in records if rec.type == EntryType.contribution}
    subcontribution_records = {rec.subcontrib_id for rec in records if rec.type == EntryType.subcontribution}
    event_records = {rec.event_id for rec in records if rec.type == EntryType.event}

    if attachment_records:
        changed_attachments.update(Attachment.query.filter(Attachment.id.in_(attachment_records)))

    if note_records:
        changed_notes.update(EventNote.query.filter(EventNote.id.in_(note_records)))

    if event_records:
        changed_events.update(Event.query.filter(Event.id.in_(event_records)))

    changed_event_ids = {ev.id for ev in changed_events}

    if changed_event_ids:
        changed_attachments.update(
            Attachment.query.filter(
                Attachment.folder.has(AttachmentFolder.linked_event_id.in_(changed_event_ids))
            )
        )
        changed_notes.update(EventNote.query.filter(EventNote.linked_event_id.in_(changed_event_ids)))

    yield from changed_events

    # Sessions are added (implictly + explicitly changed)
    if changed_event_ids or session_records:
        condition = Session.event_id.in_(changed_event_ids) & ~Session.is_deleted
        if session_records:
            condition = db.or_(condition, Session.id.in_(session_records))
        changed_sessions.update(Session.query.filter(Session.event_id.in_(changed_event_ids), ~Session.is_deleted))

    if changed_sessions:
        # XXX I kept this very similar to the structure of the code for contributions below,
        # but why aren't we just merging this into the block right above?!
        changed_session_ids = {s.id for s in changed_sessions}
        changed_contributions.update(Contribution.query
                                     .filter(Contribution.session_id.in_(changed_session_ids),
                                             ~Contribution.is_deleted))
        changed_attachments.update(
            Attachment.query.filter(
                ~Attachment.is_deleted,
                Attachment.folder.has(db.and_(AttachmentFolder.session_id.in_(changed_session_ids),
                                              ~AttachmentFolder.is_deleted))
            )
        )
        changed_notes.update(EventNote.query.filter(EventNote.session_id.in_(changed_session_ids),
                                                    ~EventNote.is_deleted))

    # Contributions are added (implictly + explicitly changed)
    if changed_event_ids or contribution_records:
        condition = Contribution.event_id.in_(changed_event_ids) & ~Contribution.is_deleted
        if contribution_records:
            condition = db.or_(condition, Contribution.id.in_(contribution_records))
        changed_contributions.update(Contribution.query.filter(condition).options(joinedload('subcontributions')))

    for contribution in changed_contributions:
        yield contribution
        changed_subcontributions.update(contribution.subcontributions)

    if changed_contributions:
        changed_contribution_ids = {c.id for c in changed_contributions}
        changed_attachments.update(
            Attachment.query.filter(
                ~Attachment.is_deleted,
                Attachment.folder.has(db.and_(AttachmentFolder.contribution_id.in_(changed_contribution_ids),
                                              ~AttachmentFolder.is_deleted))
            )
        )
        changed_notes.update(EventNote.query.filter(EventNote.contribution_id.in_(changed_contribution_ids),
                                                    ~EventNote.is_deleted))

    # Same for subcontributions
    if subcontribution_records:
        changed_subcontributions.update(SubContribution.query.filter(SubContribution.id.in_(subcontribution_records)))

    if changed_subcontributions:
        changed_subcontribution_ids = {sc.id for sc in changed_subcontributions}
        changed_attachments.update(
            Attachment.query.filter(
                ~Attachment.is_deleted,
                Attachment.folder.has(db.and_(AttachmentFolder.subcontribution_id.in_(changed_subcontribution_ids),
                                              ~AttachmentFolder.is_deleted))
            )
        )
        changed_notes.update(EventNote.query.filter(EventNote.subcontribution_id.in_(changed_subcontribution_ids),
                                                    ~EventNote.is_deleted))

    yield from changed_subcontributions
    yield from changed_attachments
    yield from changed_notes


def _process_cascaded_locations(records):
    contributions = {rec.contribution for rec in records if rec.type == EntryType.contribution}
    events = {rec.event for rec in records if rec.type == EntryType.event}
    event_ids = {e.id for e in events}
    session_ids = {rec.session_id for rec in records if rec.type == EntryType.session}

    # location of the event changed
    yield from events
    # location of the contribution changed
    yield from contributions
    # location of contributions inside an event may be inherited
    # we don't check the inheritance since we're lazy and the chain is non-trivial
    yield from Contribution.query.filter(Contribution.event_id.in_(event_ids), ~Contribution.is_deleted)
    # location of a contribution inside a session may be inherited as well
    yield from Contribution.query.filter(Contribution.session_id.in_(session_ids), ~Contribution.is_deleted)
