# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.db import db
from indico.core.db.sqlalchemy.links import LinkType
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.events import Event
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.events.sessions import Session


def get_note_query():
    """Build an ORM query which gets all notes."""
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    subcontrib_contrib = db.aliased(Contribution)
    subcontrib_session = db.aliased(Session)
    subcontrib_event = db.aliased(Event)
    session_event = db.aliased(Event)

    note_filter = db.and_(
        ~EventNote.is_deleted,
        db.or_(
            EventNote.link_type != LinkType.event,
            ~Event.is_deleted
        ),
        db.or_(
            EventNote.link_type != LinkType.contribution,
            ~Contribution.is_deleted & ~contrib_event.is_deleted
        ),
        db.or_(
            EventNote.link_type != LinkType.subcontribution,
            db.and_(
                ~SubContribution.is_deleted,
                ~subcontrib_contrib.is_deleted,
                ~subcontrib_event.is_deleted,
            )
        ),
        db.or_(
            EventNote.link_type != LinkType.session,
            ~Session.is_deleted & ~session_event.is_deleted
        )
    )

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
        .filter(note_filter)
    )


def get_attachment_query():
    """Build an ORM query which gets all attachments."""
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    subcontrib_contrib = db.aliased(Contribution)
    subcontrib_session = db.aliased(Session)
    subcontrib_event = db.aliased(Event)
    session_event = db.aliased(Event)

    attachment_filter = db.and_(
        ~Attachment.is_deleted,
        ~AttachmentFolder.is_deleted,
        db.or_(
            AttachmentFolder.link_type != LinkType.event,
            ~Event.is_deleted,
        ),
        db.or_(
            AttachmentFolder.link_type != LinkType.contribution,
            ~Contribution.is_deleted & ~contrib_event.is_deleted
        ),
        db.or_(
            AttachmentFolder.link_type != LinkType.subcontribution,
            db.and_(
                ~SubContribution.is_deleted,
                ~subcontrib_contrib.is_deleted,
                ~subcontrib_event.is_deleted
            )
        ),
        db.or_(
            AttachmentFolder.link_type != LinkType.session,
            ~Session.is_deleted & ~session_event.is_deleted
        )
    )

    return (
        Attachment.query
        .join(Attachment.folder)
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
        .filter(attachment_filter)
        .filter(AttachmentFolder.link_type != LinkType.category)
    )
