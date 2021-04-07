# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import current_app
from marshmallow import post_dump
from webargs import fields

from indico.core.db.sqlalchemy.principals import PrincipalType
from indico.core.marshmallow import mm
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.search.schemas import (AttachmentSchema, CategorySchema, ContributionSchema, EventNoteSchema,
                                           EventSchema, SubContributionSchema)
from indico.web.flask.util import url_for


PRINCIPAL_TYPES = {
    PrincipalType.user,
    PrincipalType.local_group, PrincipalType.multipass_group,
    PrincipalType.event_role, PrincipalType.category_role,
}


def _get_identifiers(access_list):
    return sorted(p.identifier for p in access_list if p.principal_type in PRINCIPAL_TYPES)


def _get_category_chain(event, categories):
    if not event:
        return None
    if categories is not None:
        return categories[event.category_id]
    return CategorySchema(many=True).dump(event.detailed_category_chain)


class ACLSchema:
    _access = fields.Method('_get_object_acl')

    def _get_acl(self, obj):
        return _get_identifiers(obj.get_access_list())

    def _get_attachment_acl(self, attachment):
        linked_object = attachment.folder.object
        manager_list = set(linked_object.get_manager_list(recursive=True))

        if attachment.is_self_protected:
            acl = {e for e in attachment.acl} | manager_list
        elif attachment.is_inheriting and attachment.folder.is_self_protected:
            acl = {e for e in attachment.folder.acl} | manager_list
        else:
            acl = linked_object.get_access_list()
        return _get_identifiers(acl)

    def _get_object_acl(self, object):
        """Return the object ACLs.

        More information here https://cern-search.docs.cern.ch/usage/permissions/
        """
        from indico_citadel.plugin import CitadelPlugin

        default_acl = CitadelPlugin.settings.get('search_owner_role')

        if isinstance(object, (Event, Contribution)):
            obj_acl = self._get_acl(object)
        elif isinstance(object, SubContribution):
            obj_acl = self._get_acl(object.contribution)
        elif isinstance(object, Attachment):
            obj_acl = self._get_attachment_acl(object)
        elif isinstance(object, EventNote):
            obj_acl = self._get_acl(object.object)
        else:
            raise ValueError(f'unknown object {object}')

        acl = {
            'owner': [default_acl],
            'update': [default_acl],
            'delete': [default_acl]
        }
        if obj_acl:
            acl['read'] = [default_acl] + obj_acl

        return acl


class RecordSchema(ACLSchema):
    class Meta:
        fields = ('_data', '_access', 'site')

    site = fields.Function(lambda _: current_app.config.get('SERVER_NAME'))
    schema = fields.Function(lambda _, ctx: ctx.get('schema'))

    @post_dump
    def remove_none_fields(self, data, **kwargs):
        """Remove fields that are None to avoid jsonschema validation errors."""
        return {
            key: value for key, value in data.items()
            if value is not None
        }


class EventRecordSchema(RecordSchema, EventSchema):
    class Meta:
        model = Event
        indexable = ('title', 'description', 'keywords', 'location', 'persons')
        non_indexable = ('type', 'type_format', 'event_id', 'url', 'category_path', 'start_dt', 'end_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda event: EventSchema(only=EventRecordSchema.Meta.indexable).dump(event))
    category_path = fields.Function(lambda e, ctx: _get_category_chain(e, ctx.get('categories')))
    # By default, CERNs global indexing requires external URLs
    url = mm.String(attribute='external_url')


class AttachmentRecordSchema(RecordSchema, AttachmentSchema):
    class Meta:
        model = Attachment
        indexable = ('title', 'filename', 'user')
        non_indexable = ('attachment_id', 'type', 'type_format', 'event_id', 'contribution_id', 'category_path',
                         'url', 'subcontribution_id', 'modified_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda at: AttachmentSchema(only=AttachmentRecordSchema.Meta.indexable).dump(at))
    category_path = fields.Function(lambda a, ctx: _get_category_chain(a.folder.event, ctx.get('categories')))
    url = mm.String(attribute='absolute_download_url')


class ContributionRecordSchema(RecordSchema, ContributionSchema):
    class Meta:
        model = Contribution
        indexable = ('title', 'description', 'location', 'persons')
        non_indexable = ('contribution_id', 'type', 'type_format', 'event_id', 'url', 'category_path', 'start_dt',
                         'end_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda contrib: ContributionSchema(
        only=ContributionRecordSchema.Meta.indexable
    ).dump(contrib))
    category_path = fields.Function(lambda c, ctx: _get_category_chain(c.event, ctx.get('categories')))
    url = mm.Function(lambda contrib: url_for('contributions.display_contribution', contrib, _external=True))


class SubContributionRecordSchema(RecordSchema, SubContributionSchema):
    class Meta:
        model = SubContribution
        indexable = ('title', 'description', 'persons', 'location')
        non_indexable = ('subcontribution_id', 'type', 'event_id', 'contribution_id', 'category_path', 'url')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda subc: SubContributionSchema(
        only=SubContributionRecordSchema.Meta.indexable
    ).dump(subc))
    category_path = fields.Function(lambda subc, ctx: _get_category_chain(subc.event, ctx.get('categories')))
    url = mm.Function(lambda subc: url_for('contributions.display_subcontribution', subc, _external=True))


class _EventNoteDataSchema(EventNoteSchema):
    class Meta:
        fields = ('title', 'content')

    title = mm.Function(lambda note: f'{note.object.title} - Notes/Minutes')


class EventNoteRecordSchema(RecordSchema, EventNoteSchema):
    class Meta:
        model = EventNote
        non_indexable = ('note_id', 'type', 'event_id', 'contribution_id', 'subcontribution_id', 'category_path',
                         'url', 'created_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda note: _EventNoteDataSchema().dump(note))
    category_path = fields.Function(lambda note, ctx: _get_category_chain(note.event, ctx.get('categories')))
    url = mm.Function(lambda note: url_for('event_notes.view', note, _external=True))
