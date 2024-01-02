# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from sqlalchemy.orm import contains_eager, joinedload, load_only, raiseload, selectinload

from indico.core.db import db
from indico.core.db.sqlalchemy.links import LinkType
from indico.modules.attachments import Attachment, AttachmentFolder
from indico.modules.attachments.models.principals import AttachmentFolderPrincipal, AttachmentPrincipal
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.principals import ContributionPrincipal
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.principals import EventPrincipal
from indico.modules.events.notes.models.notes import EventNote, EventNoteRevision
from indico.modules.events.sessions import Session
from indico.modules.events.sessions.models.blocks import SessionBlock
from indico.modules.events.sessions.models.principals import SessionPrincipal

from indico_livesync.util import get_excluded_categories


def apply_acl_entry_strategy(rel, principal):
    user_strategy = rel.joinedload('user')
    user_strategy.raiseload('*')
    user_strategy.load_only('id')
    rel.joinedload('local_group').load_only('id')
    if principal.allow_networks:
        rel.joinedload('ip_network_group').load_only('id')
    if principal.allow_category_roles:
        rel.joinedload('category_role').load_only('id')
    if principal.allow_event_roles:
        rel.joinedload('event_role').load_only('id')
    if principal.allow_registration_forms:
        rel.joinedload('registration_form').load_only('id')
    return rel


def _get_excluded_category_filter(event_model=Event):
    if excluded_category_ids := get_excluded_categories(deep=True):
        return event_model.category_id.notin_(excluded_category_ids)
    return True


def query_events(ids=None):
    if ids is None:
        export_filter = ~Event.is_deleted & _get_excluded_category_filter()
    else:
        export_filter = Event.id.in_(ids)
    return (
        Event.query
        .filter(export_filter)
        .options(
            apply_acl_entry_strategy(selectinload(Event.acl_entries), EventPrincipal),
            selectinload(Event.person_links).joinedload('person').joinedload('user').load_only('is_system'),
            joinedload(Event.own_venue),
            joinedload(Event.own_room).options(raiseload('*'), joinedload('location')),
        )
        .order_by(Event.id)
    )


def query_contributions(ids=None):
    event_strategy = contains_eager(Contribution.event)
    event_strategy.joinedload(Event.own_venue)
    event_strategy.joinedload(Event.own_room).options(raiseload('*'), joinedload('location'))
    apply_acl_entry_strategy(event_strategy.selectinload(Event.acl_entries), EventPrincipal)

    session_strategy = joinedload(Contribution.session)
    apply_acl_entry_strategy(session_strategy.selectinload(Session.acl_entries), SessionPrincipal)
    session_strategy.joinedload(Session.own_venue)
    session_strategy.joinedload(Session.own_room).options(raiseload('*'), joinedload('location'))

    session_block_strategy = joinedload(Contribution.session_block)
    session_block_strategy.joinedload(SessionBlock.own_venue)
    session_block_strategy.joinedload(SessionBlock.own_room).options(raiseload('*'), joinedload('location'))
    session_block_session_strategy = session_block_strategy.joinedload(SessionBlock.session)
    session_block_session_strategy.joinedload(Session.own_venue)
    session_block_session_strategy.joinedload(Session.own_room).options(raiseload('*'), joinedload('location'))

    if ids is None:
        export_filter = ~Contribution.is_deleted & ~Event.is_deleted & _get_excluded_category_filter()
    else:
        export_filter = Contribution.id.in_(ids)

    return (
        Contribution.query
        .join(Event)
        .filter(export_filter)
        .options(
            selectinload(Contribution.acl_entries),
            selectinload(Contribution.person_links).joinedload('person').joinedload('user').load_only('is_system'),
            event_strategy,
            session_strategy,
            session_block_strategy,
            joinedload(Contribution.type),
            joinedload(Contribution.own_venue),
            joinedload(Contribution.own_room).options(raiseload('*'), joinedload('location')),
            joinedload(Contribution.timetable_entry),
        )
        .order_by(Contribution.id)
    )


def query_subcontributions(ids=None):
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    contrib_block = db.aliased(SessionBlock)

    contrib_strategy = contains_eager(SubContribution.contribution)
    contrib_strategy.joinedload(Contribution.own_venue)
    contrib_strategy.joinedload(Contribution.own_room).options(raiseload('*'), joinedload('location'))
    contrib_strategy.joinedload(Contribution.timetable_entry)
    apply_acl_entry_strategy(contrib_strategy.selectinload(Contribution.acl_entries), ContributionPrincipal)

    event_strategy = contrib_strategy.contains_eager(Contribution.event.of_type(contrib_event))
    event_strategy.joinedload(contrib_event.own_venue)
    event_strategy.joinedload(contrib_event.own_room).options(raiseload('*'), joinedload('location'))
    apply_acl_entry_strategy(event_strategy.selectinload(contrib_event.acl_entries), EventPrincipal)

    session_strategy = contrib_strategy.contains_eager(Contribution.session.of_type(contrib_session))
    apply_acl_entry_strategy(session_strategy.selectinload(contrib_session.acl_entries), SessionPrincipal)
    session_strategy.joinedload(contrib_session.own_venue)
    session_strategy.joinedload(contrib_session.own_room).options(raiseload('*'), joinedload('location'))

    session_block_strategy = contrib_strategy.contains_eager(Contribution.session_block.of_type(contrib_block))
    session_block_strategy.joinedload(contrib_block.own_venue)
    session_block_strategy.joinedload(contrib_block.own_room).options(raiseload('*'), joinedload('location'))

    if ids is None:
        export_filter = db.and_(~SubContribution.is_deleted,
                                ~Contribution.is_deleted,
                                ~contrib_event.is_deleted,
                                _get_excluded_category_filter(contrib_event))
    else:
        export_filter = SubContribution.id.in_(ids)

    return (
        SubContribution.query
        .join(Contribution)
        .join(Contribution.event.of_type(contrib_event))
        .outerjoin(Contribution.session.of_type(contrib_session))
        .outerjoin(Contribution.session_block.of_type(contrib_block))
        .filter(export_filter)
        .options(
            selectinload(SubContribution.person_links).joinedload('person').joinedload('user').load_only('is_system'),
            contrib_strategy,
            event_strategy,
            session_strategy,
            session_block_strategy
        )
        .order_by(SubContribution.id)
    )


def query_attachments(ids=None):
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    subcontrib_contrib = db.aliased(Contribution)
    subcontrib_session = db.aliased(Session)
    subcontrib_event = db.aliased(Event)
    session_event = db.aliased(Event)

    attachment_strategy = apply_acl_entry_strategy(selectinload(Attachment.acl_entries), AttachmentPrincipal)
    folder_strategy = contains_eager(Attachment.folder)
    folder_strategy.load_only('id', 'protection_mode', 'link_type', 'category_id', 'event_id', 'linked_event_id',
                              'contribution_id', 'subcontribution_id', 'session_id')
    apply_acl_entry_strategy(folder_strategy.selectinload(AttachmentFolder.acl_entries), AttachmentFolderPrincipal)
    # event
    apply_acl_entry_strategy(folder_strategy.contains_eager(AttachmentFolder.linked_event)
                             .selectinload(Event.acl_entries), EventPrincipal)
    # contribution
    contrib_strategy = folder_strategy.contains_eager(AttachmentFolder.contribution)
    apply_acl_entry_strategy(contrib_strategy.selectinload(Contribution.acl_entries), ContributionPrincipal)
    apply_acl_entry_strategy(contrib_strategy.contains_eager(Contribution.event.of_type(contrib_event))
                             .selectinload(contrib_event.acl_entries), EventPrincipal)
    apply_acl_entry_strategy(contrib_strategy.contains_eager(Contribution.session.of_type(contrib_session))
                             .selectinload(contrib_session.acl_entries), SessionPrincipal)
    # subcontribution
    subcontrib_strategy = folder_strategy.contains_eager(AttachmentFolder.subcontribution)
    subcontrib_contrib_strategy = subcontrib_strategy.contains_eager(
        SubContribution.contribution.of_type(subcontrib_contrib)
    )
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .selectinload(subcontrib_contrib.acl_entries), ContributionPrincipal)
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .contains_eager(subcontrib_contrib.event.of_type(subcontrib_event))
                             .selectinload(subcontrib_event.acl_entries), EventPrincipal)
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .contains_eager(subcontrib_contrib.session.of_type(subcontrib_session))
                             .selectinload(subcontrib_session.acl_entries), SessionPrincipal)
    # session
    session_strategy = folder_strategy.contains_eager(AttachmentFolder.session)
    session_strategy.contains_eager(Session.event.of_type(session_event)).selectinload(session_event.acl_entries)
    apply_acl_entry_strategy(session_strategy.selectinload(Session.acl_entries), SessionPrincipal)

    if ids is None:
        export_filter = db.and_(
            ~Attachment.is_deleted,
            ~AttachmentFolder.is_deleted,
            db.or_(
                AttachmentFolder.link_type != LinkType.event,
                ~Event.is_deleted & _get_excluded_category_filter(),
            ),
            db.or_(
                AttachmentFolder.link_type != LinkType.contribution,
                ~Contribution.is_deleted & ~contrib_event.is_deleted & _get_excluded_category_filter(contrib_event)
            ),
            db.or_(
                AttachmentFolder.link_type != LinkType.subcontribution,
                db.and_(
                    ~SubContribution.is_deleted,
                    ~subcontrib_contrib.is_deleted,
                    ~subcontrib_event.is_deleted,
                    _get_excluded_category_filter(subcontrib_event)
                )
            ),
            db.or_(
                AttachmentFolder.link_type != LinkType.session,
                ~Session.is_deleted & ~session_event.is_deleted & _get_excluded_category_filter(session_event)
            )
        )
    else:
        export_filter = Attachment.id.in_(ids)

    return (
        Attachment.query
        .join(Attachment.folder)
        .options(folder_strategy, attachment_strategy, joinedload(Attachment.user))
        .outerjoin(AttachmentFolder.linked_event)
        .outerjoin(AttachmentFolder.contribution)
        .outerjoin(Contribution.event.of_type(contrib_event))
        .outerjoin(Contribution.session.of_type(contrib_session))
        .outerjoin(AttachmentFolder.subcontribution)
        .outerjoin(SubContribution.contribution.of_type(subcontrib_contrib))
        .outerjoin(subcontrib_contrib.event.of_type(subcontrib_event))
        .outerjoin(subcontrib_contrib.session.of_type(subcontrib_session))
        .outerjoin(AttachmentFolder.session)
        .outerjoin(Session.event.of_type(session_event))
        .filter(export_filter)
        .filter(AttachmentFolder.link_type != LinkType.category)
        .order_by(Attachment.id)
    )


def query_notes(ids=None):
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    subcontrib_contrib = db.aliased(Contribution)
    subcontrib_session = db.aliased(Session)
    subcontrib_event = db.aliased(Event)
    session_event = db.aliased(Event)

    note_strategy = load_only('id', 'link_type', 'event_id', 'linked_event_id', 'contribution_id',
                              'subcontribution_id', 'session_id', 'html')
    # event
    apply_acl_entry_strategy(note_strategy.contains_eager(EventNote.linked_event)
                             .selectinload(Event.acl_entries), EventPrincipal)
    # contribution
    contrib_strategy = note_strategy.contains_eager(EventNote.contribution)
    apply_acl_entry_strategy(contrib_strategy.selectinload(Contribution.acl_entries), ContributionPrincipal)
    apply_acl_entry_strategy(contrib_strategy.contains_eager(Contribution.event.of_type(contrib_event))
                             .selectinload(contrib_event.acl_entries), EventPrincipal)
    apply_acl_entry_strategy(contrib_strategy.contains_eager(Contribution.session.of_type(contrib_session))
                             .selectinload(contrib_session.acl_entries), SessionPrincipal)
    # subcontribution
    subcontrib_strategy = note_strategy.contains_eager(EventNote.subcontribution)
    subcontrib_contrib_strategy = subcontrib_strategy.contains_eager(
        SubContribution.contribution.of_type(subcontrib_contrib)
    )
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .selectinload(subcontrib_contrib.acl_entries), ContributionPrincipal)
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .contains_eager(subcontrib_contrib.event.of_type(subcontrib_event))
                             .selectinload(subcontrib_event.acl_entries), EventPrincipal)
    apply_acl_entry_strategy(subcontrib_contrib_strategy
                             .contains_eager(subcontrib_contrib.session.of_type(subcontrib_session))
                             .selectinload(subcontrib_session.acl_entries), SessionPrincipal)
    # session
    session_strategy = note_strategy.contains_eager(EventNote.session)
    session_strategy.contains_eager(Session.event.of_type(session_event)).selectinload(session_event.acl_entries)
    apply_acl_entry_strategy(session_strategy.selectinload(Session.acl_entries), SessionPrincipal)

    if ids is None:
        export_filter = db.and_(
            ~EventNote.is_deleted,
            db.or_(
                EventNote.link_type != LinkType.event,
                ~Event.is_deleted & _get_excluded_category_filter()
            ),
            db.or_(
                EventNote.link_type != LinkType.contribution,
                ~Contribution.is_deleted & ~contrib_event.is_deleted & _get_excluded_category_filter(contrib_event)
            ),
            db.or_(
                EventNote.link_type != LinkType.subcontribution,
                db.and_(
                    ~SubContribution.is_deleted,
                    ~subcontrib_contrib.is_deleted,
                    ~subcontrib_event.is_deleted,
                    _get_excluded_category_filter(subcontrib_event)
                )
            ),
            db.or_(
                EventNote.link_type != LinkType.session,
                ~Session.is_deleted & ~session_event.is_deleted & _get_excluded_category_filter(session_event)
            )
        )
    else:
        export_filter = EventNote.id.in_(ids)

    return (
        EventNote.query
        .outerjoin(EventNote.linked_event)
        .outerjoin(EventNote.contribution)
        .outerjoin(Contribution.event.of_type(contrib_event))
        .outerjoin(Contribution.session.of_type(contrib_session))
        .outerjoin(EventNote.subcontribution)
        .outerjoin(SubContribution.contribution.of_type(subcontrib_contrib))
        .outerjoin(subcontrib_contrib.event.of_type(subcontrib_event))
        .outerjoin(subcontrib_contrib.session.of_type(subcontrib_session))
        .outerjoin(EventNote.session)
        .outerjoin(Session.event.of_type(session_event))
        .filter(export_filter)
        .options(
            note_strategy,
            joinedload(EventNote.current_revision).joinedload(EventNoteRevision.user),
        )
        .order_by(EventNote.id)
    )
