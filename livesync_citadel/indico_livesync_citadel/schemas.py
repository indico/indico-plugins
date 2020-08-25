# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import itertools
from marshmallow import post_dump
from tika import parser
from webargs import fields

from indico.core.db.sqlalchemy.links import LinkType
from indico.core.db.sqlalchemy.principals import PrincipalType
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.core.marshmallow import mm
from indico.modules.attachments.models.attachments import Attachment, AttachmentType
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.web.flask.util import url_for


def _get_identifiers(principal):
    if (principal.principal_type == PrincipalType.user
            or principal.principal_type == PrincipalType.event_role
            or principal.principal_type == PrincipalType.category_role):
        yield principal.identifier
        yield principal.email
    elif principal.is_group:
        yield principal.identifier


class ACLSchema(object):
    _access = fields.Method('_get_object_acl')

    def _get_event_acl(self, event):
        if event.effective_protection_mode == ProtectionMode.public:
            return []
        return set(itertools.chain.from_iterable(_get_identifiers(x) for x in event.get_access_list()))

    def _get_acl(self, obj):
        if obj.is_self_protected:
            principals = {p for p in obj.acl} | set(obj.get_manager_list(recursive=True))
        elif obj.is_inheriting and obj.is_self_protected:
            principals = {p for p in obj.acl} | set(obj.get_manager_list(recursive=True))
        else:
            principals = obj.get_access_list()
        return sorted(set(itertools.chain.from_iterable(_get_identifiers(x) for x in principals)))

    def _get_event_note_acl(self, note):
        contribution = None
        if note.contribution or note.subcontribution:
            contribution = note.subcontribution.contribution if note.subcontribution else note.contribution

        if contribution:
            return self._get_acl(contribution)
        elif note.session:
            return self._get_acl(note.session)
        else:
            return self._get_event_acl(note.event)

    def _get_object_acl(self, object):
        """Return the object ACLs.

        More information here https://cern-search.docs.cern.ch/usage/permissions/
        """
        from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin

        default_acl = LiveSyncCitadelPlugin.settings.get('search_owner_role')
        read_acl = [default_acl]

        if isinstance(object, Event):
            read_acl.extend(self._get_event_acl(object))
        elif isinstance(object, Contribution):
            read_acl.extend(self._get_acl(object))
        elif isinstance(object, SubContribution):
            read_acl.extend(self._get_acl(object.contribution))
        elif isinstance(object, Attachment):
            read_acl.extend(self._get_acl(object.folder.object))
        elif isinstance(object, EventNote):
            read_acl.extend(self._get_event_note_acl(object))
        else:
            raise ValueError('unknown object {}'.format(object))

        return {
            'read': read_acl,
            'owner': [default_acl],
            'update': [default_acl],
            'delete': [default_acl]
        }


def _get_location(obj):
    if obj.venue_name and obj.room_name:
        return '{}: {}'.format(obj.venue_name, obj.room_name)
    elif obj.venue_name or obj.room_name:
        return obj.venue_name or obj.room_name
    else:
        return ''


def _get_category_path(obj):
    if isinstance(obj, Event):
        event = obj
    elif isinstance(obj, Attachment):
        event = obj.folder.event
    else:
        event = obj.event
    return event.category.chain_titles


def _get_people_list(obj):
    return [
        '{} ({})'.format(pl.full_name, pl.affiliation) if pl.affiliation else pl.full_name
        for pl in obj.person_links
    ]


class _EventDataSchema(mm.ModelSchema):
    id = fields.Int()
    category_path = fields.Function(_get_category_path)
    event_type = fields.Str(attribute='type')
    title = fields.Str()
    description = fields.Str()
    location = fields.Function(_get_location)
    speakers_chairs = fields.Function(_get_people_list)
    url = fields.Str(attribute='external_url')

    class Meta:
        model = Event
        fields = ('id', 'category_path', 'event_type', 'title', 'description', 'location', 'speakers_chairs', 'url')


class EventSchema(ACLSchema, mm.Schema):
    _data = fields.Function(lambda event: _EventDataSchema().dump(event))
    creation_date = fields.DateTime(attribute='created_dt', format='%Y-%m-%dT%H:%M')
    start_date = fields.DateTime(attribute='start_dt', format='%Y-%m-%dT%H:%M')
    end_date = fields.DateTime(attribute='end_dt', format='%Y-%m-%dT%H:%M')


class _AttachmentDataSchema(mm.ModelSchema):
    id = fields.Int()
    category_path = fields.Function(_get_category_path)
    event_id = fields.Int(attribute='folder.event.id')
    contribution_id = fields.Method('_get_attachment_contrib_id')
    subcontribution_id = fields.Method('_get_attachment_subcontrib_id')
    filename = fields.Str(attribute='file.filename')
    content = fields.Method('_get_attachment_content')
    url = fields.Str(attribute='absolute_download_url')

    class Meta:
        model = Attachment
        fields = ('id', 'category_path', 'event_id', 'contribution_id', 'subcontribution_id', 'filename', 'content',
                  'url')

    def _get_attachment_subcontrib_id(self, attachment):
        return attachment.folder.subcontribution.id if attachment.folder.link_type == LinkType.subcontribution else None

    def _get_attachment_contrib_id(self, attachment):
        return attachment.folder.contribution.id if attachment.folder.link_type == LinkType.contribution else None

    def _get_attachment_content(self, attachment):
        if attachment.type == AttachmentType.file:
            from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin
            return parser.from_file(attachment.absolute_download_url,
                                    LiveSyncCitadelPlugin.settings.get('tika_server'))['content']


class AttachmentSchema(ACLSchema, mm.Schema):
    _data = fields.Function(lambda attachment: _AttachmentDataSchema().dump(attachment))
    creation_date = fields.DateTime(attribute='modified_dt', format='%Y-%m-%dT%H:%M')


class _ContributionDataSchema(mm.ModelSchema):
    id = fields.Int()
    category_path = fields.Function(_get_category_path)
    event_id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    location = fields.Function(_get_location)
    list_of_persons = fields.Function(_get_people_list)
    url = fields.Function(lambda contrib: url_for('contributions.display_contribution', contrib, _external=True))

    class Meta:
        model = Contribution
        fields = ('id', 'category_path', 'event_id', 'title', 'description', 'location', 'list_of_persons', 'url')


class ContributionSchema(ACLSchema, mm.Schema):
    _data = fields.Function(lambda contrib: _ContributionDataSchema().dump(contrib))
    start_date = fields.DateTime(attribute='start_dt', format='%Y-%m-%dT%H:%M')
    end_date = fields.DateTime(attribute='end_dt', format='%Y-%m-%dT%H:%M')

    @post_dump
    def remove_none_fields(self, data):
        """Remove fields that are None to avoid jsonschema validation errors."""
        return {
            key: value for key, value in data.items()
            if value is not None
        }


class _SubContributionDataSchema(mm.ModelSchema):
    id = fields.Int()
    category_path = fields.Function(_get_category_path)
    event_id = fields.Int()
    contribution_id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    location = fields.Function(lambda subcontrib: _get_location(subcontrib.contribution))
    list_of_persons = fields.Function(_get_people_list)
    url = fields.Function(lambda subcontrib: url_for('contributions.display_subcontribution',
                                                     subcontrib, _external=True))

    class Meta:
        model = SubContribution
        fields = ('id', 'category_path', 'event_id', 'contribution_id', 'title', 'description', 'location',
                  'list_of_persons', 'url')


class SubContributionSchema(ACLSchema, mm.Schema):
    _data = fields.Function(lambda subcontrib: _SubContributionDataSchema().dump(subcontrib))


class _EventNoteDataSchema(mm.ModelSchema):
    id = fields.Int()
    category_path = fields.Function(_get_category_path)
    event_id = fields.Int()
    url = fields.Function(lambda note: url_for('event_notes.view', note, _external=True))
    content = fields.Str(attribute='html')
    contribution_id = fields.Method('_get_contribution_id')
    subcontribution_id = fields.Int()
    session_id = fields.Function(lambda note: note.session.id if note.session else None)

    class Meta:
        model = EventNote
        fields = ('id', 'category_path', 'event_id', 'content', 'url', 'contribution_id', 'subcontribution_id',
                  'session_id')

    def _get_contribution_id(self, note):
        if note.contribution:
            return note.contribution.id
        elif note.subcontribution:
            return note.subcontribution.contribution.id
        else:
            return None

    @post_dump
    def remove_none_fields(self, data):
        """Remove fields that are None to avoid jsonschema validation errors."""
        return {
            key: value for key, value in data.items()
            if value is not None
        }


class EventNoteSchema(ACLSchema, mm.Schema):
    _data = fields.Function(lambda note: _EventNoteDataSchema().dump(note))
    creation_date = fields.DateTime(attribute='current_revision.created_dt', format='%Y-%m-%dT%H:%M')
