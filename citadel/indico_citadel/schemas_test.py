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

from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.core.marshmallow import mm
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
    dummy_event.description = 'A dummy <strong>event</strong>'
    dummy_event.keywords = ['foo', 'bar']
    person = EventPerson.create_from_user(dummy_user, dummy_event)
    person2 = EventPerson(event=dummy_event, first_name='Admin', last_name='Saurus', affiliation='Indico')
    dummy_event.person_links.append(EventPersonLink(person=person))
    dummy_event.person_links.append(EventPersonLink(person=person2))
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
            'persons': [{'name': 'Guinea Pig'},
                        {'affiliation': 'Indico', 'name': 'Admin Saurus'}],
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
    dummy_contribution.description = 'A dummy <strong>contribution</strong>'

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
            'persons': [{'name': 'Guinea Pig'}],
            'site': 'http://localhost',
            'title': 'Dummy Contribution',
        },
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'duration': 20,
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
                                      description='A dummy <strong>subcontribution</strong>',
                                      duration=timedelta(minutes=10))

    person = EventPerson.create_from_user(dummy_user, dummy_event)
    subcontribution.person_links.append(SubContributionPersonLink(person=person))

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
            'persons': [{'name': 'Guinea Pig'}],
            'site': 'http://localhost',
            'title': 'Dummy Subcontribution',
        },
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'duration': 10,
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
            'persons': {'name': 'Guinea Pig'},
        },
        'attachment_id': attachment.id,
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'contribution_id': dummy_contribution.id,
        'event_id': 0,
        'folder_id': folder.id,
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
    from .schemas import EventNoteRecordSchema

    if link_type == 'event':
        ids = {}
        note = EventNote(object=dummy_event)
        url = '/event/0/note/'
    elif link_type == 'contrib':
        ids = {'contribution_id': dummy_contribution.id}
        note = EventNote(object=dummy_contribution)
        url = f'/event/0/contributions/{dummy_contribution.id}/note/'
    elif link_type == 'subcontrib':
        subcontribution = SubContribution(contribution=dummy_contribution, title='Dummy Subcontribution',
                                          duration=timedelta(minutes=10))
        db.session.flush()
        ids = {
            'contribution_id': subcontribution.contribution_id,
            'subcontribution_id': subcontribution.id,
        }
        note = EventNote(object=subcontribution)
        url = f'/event/0/contributions/{dummy_contribution.id}/subcontributions/{subcontribution.id}/note/'

    note.create_revision(RenderMode.html, 'this is a dummy <strong>note</strong>', dummy_user)
    db.session.flush()
    category_id = dummy_event.category_id
    schema = EventNoteRecordSchema(context={'schema': 'test-notes'})
    assert schema.dump(note) == {
        '$schema': 'test-notes',
        '_access': {
            'delete': ['IndicoAdmin'],
            'owner': ['IndicoAdmin'],
            'update': ['IndicoAdmin'],
        },
        '_data': {
            'content': 'this is a dummy note',
            'site': 'http://localhost',
            'title': note.object.title,
            'persons': {'name': 'Guinea Pig'}
        },
        'category_id': category_id,
        'category_path': [
            {'id': 0, 'title': 'Home', 'url': '/'},
            {'id': category_id, 'title': 'dummy', 'url': f'/category/{category_id}/'},
        ],
        'modified_dt': note.current_revision.created_dt.isoformat(),
        'event_id': 0,
        'note_id': note.id,
        'type': 'event_note',
        'url': f'http://localhost{url}',
        **ids
    }


def test_event_acls(dummy_event, create_user):
    from .schemas import ACLSchema

    class TestSchema(ACLSchema, mm.Schema):
        pass

    def assert_acl(expected_read_acl):
        __tracebackhide__ = True
        data = schema.dump(dummy_event)
        read_acl = data['_access'].pop('read', None)
        assert data == {'_access': {'delete': ['IndicoAdmin'], 'owner': ['IndicoAdmin'], 'update': ['IndicoAdmin']}}
        if read_acl is not None:
            read_acl = set(read_acl)
        assert read_acl == expected_read_acl

    schema = TestSchema()
    u1 = create_user(1, email='user1@example.com')
    u2 = create_user(2, email='user2@example.com')
    u3 = create_user(3, email='user3@example.com')

    # event is inheriting public, so no acl
    assert_acl(None)

    # event is protected and the acl is empty (nobody has regular access)
    dummy_event.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin'})

    dummy_event.update_principal(u1, read_access=True)
    dummy_event.category.update_principal(u2, read_access=True)
    dummy_event.category.parent.update_principal(u3, read_access=True)

    # self-protected, so no acl inherited
    assert_acl({'IndicoAdmin', 'User:1'})

    # event is inheriting from public categories, so there is no acl
    dummy_event.protection_mode = ProtectionMode.inheriting
    assert_acl(None)

    # event it itself public, so no acl here as well
    dummy_event.protection_mode = ProtectionMode.public
    assert_acl(None)

    # inheriting, so all parent acl entries
    dummy_event.protection_mode = ProtectionMode.inheriting
    dummy_event.category.parent.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:1', 'User:2', 'User:3'})

    # category protected, so no parent category acl inherited
    dummy_event.category.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:1', 'User:2'})

    # parent category acl entry is a manager, that one is inherited
    dummy_event.category.parent.update_principal(u3, full_access=True)
    assert_acl({'IndicoAdmin', 'User:1', 'User:2', 'User:3'})


def test_attachment_acls(dummy_event, dummy_user, create_user):
    from .schemas import ACLSchema

    class TestSchema(ACLSchema, mm.Schema):
        pass

    folder = AttachmentFolder(title='Dummy Folder', description='a dummy folder')
    attachment = Attachment(folder=folder, user=dummy_user, title='Dummy Attachment', type=AttachmentType.link,
                            link_url='https://example.com')
    attachment.folder.object = dummy_event

    def assert_acl(expected_read_acl):
        __tracebackhide__ = True
        data = schema.dump(attachment)
        read_acl = data['_access'].pop('read', None)
        assert data == {'_access': {'delete': ['IndicoAdmin'], 'owner': ['IndicoAdmin'], 'update': ['IndicoAdmin']}}
        if read_acl is not None:
            read_acl = set(read_acl)
        assert read_acl == expected_read_acl

    schema = TestSchema()
    u1 = create_user(1, email='user1@example.com')
    u2 = create_user(2, email='user2@example.com')
    u3 = create_user(3, email='user3@example.com')

    # event is inheriting public, so no acl
    assert_acl(None)

    # event is protected and the acl is empty (nobody has regular access)
    dummy_event.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin'})

    dummy_event.update_principal(u1, read_access=True)
    dummy_event.category.update_principal(u2, read_access=True)
    dummy_event.category.parent.update_principal(u3, read_access=True)

    # self-protected, so no acl inherited
    assert_acl({'IndicoAdmin', 'User:1'})

    # event is inheriting from public categories, so there is no acl
    dummy_event.protection_mode = ProtectionMode.inheriting
    assert_acl(None)

    # event it itself public, so no acl here as well
    dummy_event.protection_mode = ProtectionMode.public
    assert_acl(None)

    # inheriting, so all parent acl entries
    dummy_event.protection_mode = ProtectionMode.inheriting
    dummy_event.category.parent.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:1', 'User:2', 'User:3'})

    # category protected, so no parent category acl inherited
    dummy_event.category.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:1', 'User:2'})

    # parent category acl entry is a manager, that one is inherited
    dummy_event.category.parent.update_principal(u3, full_access=True)
    assert_acl({'IndicoAdmin', 'User:1', 'User:2', 'User:3'})

    # attachment self-protected, only the category/event manager has access
    folder.update_principal(u2, read_access=True)
    attachment.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:3'})

    # the user in the attachment acl has access as well
    attachment.update_principal(u1, read_access=True)
    attachment.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:3', 'User:1'})

    # attachment inheriting from self-protected folder - only the folder acl is used
    attachment.protection_mode = ProtectionMode.inheriting
    folder.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin', 'User:3', 'User:2'})


@pytest.mark.parametrize('obj_type', ('event', 'contrib', 'subcontrib', 'attachment', 'note'))
def test_acls(dummy_event, dummy_contribution, dummy_user, create_user, obj_type):
    from .schemas import ACLSchema

    class TestSchema(ACLSchema, mm.Schema):
        pass

    if obj_type == 'event':
        obj = dummy_event
    elif obj_type == 'contrib':
        obj = dummy_contribution
    elif obj_type == 'subcontrib':
        obj = SubContribution(contribution=dummy_contribution, title='Test', duration=timedelta(minutes=10))
    elif obj_type == 'attachment':
        folder = AttachmentFolder(title='Dummy Folder', description='a dummy folder')
        obj = Attachment(folder=folder, user=dummy_user, title='Dummy Attachment', type=AttachmentType.link,
                         link_url='https://example.com')
        obj.folder.object = dummy_event
    elif obj_type == 'note':
        obj = EventNote(object=dummy_event)
        obj.create_revision(RenderMode.html, 'this is a dummy note', dummy_user)

    def assert_acl(expected_read_acl):
        __tracebackhide__ = True
        data = schema.dump(obj)
        read_acl = data['_access'].pop('read', None)
        assert data == {'_access': {'delete': ['IndicoAdmin'], 'owner': ['IndicoAdmin'], 'update': ['IndicoAdmin']}}
        if read_acl is not None:
            read_acl = set(read_acl)
        assert read_acl == expected_read_acl

    schema = TestSchema()
    user = create_user(1, email='user1@example.com')

    # everything is public
    assert_acl(None)

    # event is protected and the acl is empty (nobody has regular access)
    dummy_event.protection_mode = ProtectionMode.protected
    assert_acl({'IndicoAdmin'})

    # user on the acl has access
    dummy_event.update_principal(user, read_access=True)
    assert_acl({'IndicoAdmin', 'User:1'})
