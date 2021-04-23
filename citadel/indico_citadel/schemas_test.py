# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime, timedelta
from io import BytesIO

import pytest
from pytz import utc

from indico.modules.attachments.models.attachments import Attachment, AttachmentFile, AttachmentType
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.modules.events.contributions.models.persons import ContributionPersonLink, SubContributionPersonLink
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.persons import EventPerson, EventPersonLink
from indico.modules.events.notes.models.notes import EventNote, RenderMode


pytest_plugins = 'indico.modules.events.timetable.testing.fixtures'


def test_dump_event(db, dummy_user, dummy_event):
    from .schemas import EventRecordSchema

    schema = EventRecordSchema(context={'schema': 'test-events'})
    dummy_event.description = 'A dummy event'
    dummy_event.keywords = ['foo', 'bar']
    person = EventPerson.create_from_user(dummy_user, dummy_event)
    dummy_event.person_links.append(EventPersonLink(person=person))
    db.session.flush()
    category_id = dummy_event.category_id
    assert schema.dump(dummy_event) == {
        '$schema': 'test-events',
        '_access': {
            'delete': ['IndicoAdmin'],
            'owner': ['IndicoAdmin'],
            'update': ['IndicoAdmin'],
        },
        '_data': {
            'description': 'A dummy event',
            'keywords': ['foo', 'bar'],
            'location': {'address': '', 'room_name': '', 'venue_name': ''},
            'persons': [{'affiliation': '', 'name': 'Guinea Pig'}],
            'site': 'http://localhost',
            'title': 'dummy#0'
        },
        'category_id': 1,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'end_dt': dummy_event.end_dt.isoformat(),
        'event_id': 0,
        'start_dt': dummy_event.start_dt.isoformat(),
        'type': 'event',
        'type_format': 'meeting',
        'url': 'http://localhost/event/0/',
    }


@pytest.mark.parametrize('scheduled', (False, True))
def test_dump_contribution(db, dummy_user, dummy_event, dummy_contribution, create_entry, scheduled):
    from .schemas import ContributionRecordSchema

    person = EventPerson.create_from_user(dummy_user, dummy_event)
    dummy_contribution.person_links.append(ContributionPersonLink(person=person))
    dummy_contribution.description = 'A dummy contribution'

    extra = {}
    if scheduled:
        create_entry(dummy_contribution, utc.localize(datetime(2020, 4, 20, 4, 20)))
        extra = {
            'start_dt': dummy_contribution.start_dt.isoformat(),
            'end_dt': dummy_contribution.end_dt.isoformat(),
        }

    db.session.flush()
    category_id = dummy_contribution.event.category_id
    schema = ContributionRecordSchema(context={'schema': 'test-contribs'})
    assert schema.dump(dummy_contribution) == {
        '$schema': 'test-contribs',
        '_access': {
            'delete': ['IndicoAdmin'],
            'owner': ['IndicoAdmin'],
            'update': ['IndicoAdmin'],
        },
        '_data': {
            'description': 'A dummy contribution',
            'location': {'address': '', 'room_name': '', 'venue_name': ''},
            'persons': [{'affiliation': '', 'name': 'Guinea Pig'}],
            'site': 'http://localhost',
            'title': 'Dummy Contribution',
        },
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'event_id': 0,
        'type': 'contribution',
        'url': f'http://localhost/event/0/contributions/{dummy_contribution.id}/',
        **extra
    }


@pytest.mark.parametrize('scheduled', (False, True))
def test_dump_subcontribution(db, dummy_user, dummy_event, dummy_contribution, create_entry, scheduled):
    from .schemas import SubContributionRecordSchema

    extra = {}
    if scheduled:
        create_entry(dummy_contribution, utc.localize(datetime(2020, 4, 20, 4, 20)))
        extra = {
            'start_dt': dummy_contribution.start_dt.isoformat(),
            'end_dt': dummy_contribution.end_dt.isoformat(),
        }

    subcontribution = SubContribution(contribution=dummy_contribution, title='Dummy Subcontribution',
                                      description='', duration=timedelta(minutes=10))

    person = EventPerson.create_from_user(dummy_user, dummy_event)
    subcontribution.person_links.append(SubContributionPersonLink(person=person))
    subcontribution.description = 'A dummy subcontribution'

    db.session.flush()
    category_id = dummy_contribution.event.category_id
    schema = SubContributionRecordSchema(context={'schema': 'test-subcontribs'})
    assert schema.dump(subcontribution) == {
        '$schema': 'test-subcontribs',
        '_access': {
            'delete': ['IndicoAdmin'],
            'owner': ['IndicoAdmin'],
            'update': ['IndicoAdmin'],
        },
        '_data': {
            'description': 'A dummy subcontribution',
            'location': {'address': '', 'room_name': '', 'venue_name': ''},
            'persons': [{'affiliation': '', 'name': 'Guinea Pig'}],
            'site': 'http://localhost',
            'title': 'Dummy Subcontribution',
        },
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'event_id': 0,
        'subcontribution_id': subcontribution.id,
        'type': 'subcontribution',
        'url': f'http://localhost/event/0/contributions/{dummy_contribution.id}/subcontributions/{subcontribution.id}',
        **extra
    }


def test_dump_attachment(db, dummy_user, dummy_contribution):
    from .schemas import AttachmentRecordSchema

    folder = AttachmentFolder(title='Dummy Folder', description='a dummy folder')
    file = AttachmentFile(user=dummy_user, filename='dummy_file.txt', content_type='text/plain')
    attachment = Attachment(folder=folder, user=dummy_user, title='Dummy Attachment', type=AttachmentType.file,
                            file=file)
    attachment.folder.object = dummy_contribution
    attachment.file.save(BytesIO(b'hello world'))
    db.session.flush()

    category_id = dummy_contribution.event.category_id
    schema = AttachmentRecordSchema(context={'schema': 'test-attachment'})
    assert schema.dump(attachment) == {
        '$schema': 'test-attachment',
        '_access': {
            'delete': ['IndicoAdmin'],
            'owner': ['IndicoAdmin'],
            'update': ['IndicoAdmin'],
        },
        '_data': {
            'filename': 'dummy_file.txt',
            'site': 'http://localhost',
            'title': 'Dummy Attachment',
            'user': {'affiliation': None, 'name': 'Guinea Pig'},
        },
        'attachment_id': attachment.id,
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'event_id': 0,
        'modified_dt': attachment.modified_dt.isoformat(),
        'type': 'attachment',
        'type_format': 'file',
        'url': (
            f'http://localhost/event/0/contributions/'
            f'{dummy_contribution.id}/attachments/{folder.id}/{attachment.id}/dummy_file.txt'
        ),
    }


@pytest.mark.parametrize('link_type', ('event', 'contrib', 'subcontrib'))
def test_dump_event_note(db, dummy_user, dummy_event, dummy_contribution, link_type):
    from .schemas import EventNoteSchema

    if link_type == 'event':
        contribution_id = None
        subcontribution_id = None
        note = EventNote(object=dummy_event)
        url = '/event/0/note/'
    elif link_type == 'contrib':
        contribution_id = dummy_contribution.id
        subcontribution_id = None
        note = EventNote(object=dummy_contribution)
        url = f'/event/0/contributions/{contribution_id}/note/'
    elif link_type == 'subcontrib':
        subcontribution = SubContribution(contribution=dummy_contribution, title='Dummy Subcontribution',
                                          duration=timedelta(minutes=10))
        db.session.flush()
        contribution_id = None
        subcontribution_id = subcontribution.id
        note = EventNote(object=subcontribution)
        url = f'/event/0/contributions/{dummy_contribution.id}/subcontributions/{subcontribution_id}/note/'

    note.create_revision(RenderMode.html, 'this is a dummy note', dummy_user)
    db.session.flush()
    category_id = dummy_event.category_id
    schema = EventNoteSchema(context={'schema': 'test-notes'})
    assert schema.dump(note) == {
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'content': 'this is a dummy note',
        'contribution_id': contribution_id,
        'created_dt': note.current_revision.created_dt.isoformat(),
        'event_id': 0,
        'note_id': note.id,
        'subcontribution_id': subcontribution_id,
        'type': 'event_note',
        'url': url,
    }
