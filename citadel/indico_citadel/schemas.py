# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from marshmallow import post_dump
from webargs import fields

from indico.core.config import config
from indico.core.db.sqlalchemy.principals import PrincipalType
from indico.core.marshmallow import mm
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.search.schemas import (AttachmentSchema, CategorySchema, ContributionSchema, EventNoteSchema,
                                           EventSchema, SubContributionSchema)
from indico.util.string import strip_tags
from indico.web.flask.util import url_for

from indico_citadel.util import remove_none_entries


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
        if isinstance(obj, SubContribution):
            obj = obj.contribution

        if obj.is_public or not obj.is_protected:
            # is_public is a cheaper check, while is_protected climbs up the chain
            # until the first non-inheriting protection parent, so we can short-circuit
            # the check
            return None
        return _get_identifiers(obj.get_access_list())

    def _get_attachment_acl(self, attachment):
        linked_object = attachment.folder.object
        manager_list = set(linked_object.get_manager_list(recursive=True))

        if attachment.is_self_protected:
            return _get_identifiers(set(attachment.acl) | manager_list)
        elif attachment.is_inheriting and attachment.folder.is_self_protected:
            return _get_identifiers(set(attachment.folder.acl) | manager_list)
        else:
            return self._get_acl(linked_object)

    def _get_object_acl(self, object):
        """Return the object ACLs.

        More information here https://cern-search.docs.cern.ch/usage/permissions/
        """
        default_acl = 'IndicoAdmin'

        if isinstance(object, (Event, Contribution)):
            obj_acl = self._get_acl(object)
        elif isinstance(object, SubContribution):
            obj_acl = self._get_acl(object.contribution)
        elif isinstance(object, Attachment):
            obj_acl = self._get_attachment_acl(object)
        elif isinstance(object, EventNote):
            obj_acl = self._get_acl(object.object)
        else:
            raise TypeError(f'unknown object {object}')

        acl = {
            'owner': [default_acl],
            'update': [default_acl],
            'delete': [default_acl]
        }
        if obj_acl is not None:
            acl['read'] = [default_acl, *obj_acl]

        return acl


class RecordSchema(ACLSchema):
    class Meta:
        fields = ('_data', '_access', 'schema')

    schema = fields.Function(lambda _, ctx: ctx.get('schema'), data_key='$schema')

    @post_dump
    def remove_none_fields(self, data, **kwargs):
        """Remove fields that are None to avoid json schema validation errors."""
        return remove_none_entries(data)

    @post_dump
    def site(self, data, **kwargs):
        if data['_data']:
            data['_data']['site'] = config.BASE_URL
        return data


class EventRecordSchema(RecordSchema, EventSchema):
    class Meta:
        model = Event
        indexable = ('title', 'description', 'keywords', 'location', 'persons')
        non_indexable = ('type', 'event_type', 'event_id', 'url', 'category_id', 'category_path', 'start_dt', 'end_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda event: EventSchema(only=EventRecordSchema.Meta.indexable).dump(event))
    category_path = fields.Function(lambda e, ctx: _get_category_chain(e, ctx.get('categories')))
    # By default, CERNs global indexing requires external URLs
    url = mm.String(attribute='external_url')

    @post_dump
    def _transform(self, data, **kwargs):
        data['type_format'] = data.pop('event_type')
        if desc := data['_data'].get('description'):
            data['_data']['description'] = strip_tags(desc).strip()
        return data


class AttachmentRecordSchema(RecordSchema, AttachmentSchema):
    class Meta:
        model = Attachment
        indexable = ('title', 'filename', 'user')
        non_indexable = ('attachment_id', 'folder_id', 'type', 'attachment_type', 'event_id', 'contribution_id',
                         'category_id', 'category_path', 'url', 'subcontribution_id', 'modified_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda at: AttachmentSchema(only=AttachmentRecordSchema.Meta.indexable).dump(at))
    category_path = fields.Function(lambda a, ctx: _get_category_chain(a.folder.event, ctx.get('categories')))
    url = mm.String(attribute='absolute_download_url')

    @post_dump
    def _translate_keys(self, data, **kwargs):
        data['type_format'] = data.pop('attachment_type')
        if user := data['_data'].pop('user', None):
            data['_data']['persons'] = user
        return data


class ContributionRecordSchema(RecordSchema, ContributionSchema):
    class Meta:
        model = Contribution
        indexable = ('title', 'description', 'location', 'persons')
        non_indexable = ('contribution_id', 'type', 'contribution_type', 'event_id', 'url', 'category_id',
                         'category_path', 'start_dt', 'end_dt', 'duration')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda contrib: ContributionSchema(
        only=ContributionRecordSchema.Meta.indexable
    ).dump(contrib))
    category_path = fields.Function(lambda c, ctx: _get_category_chain(c.event, ctx.get('categories')))
    url = mm.Function(lambda contrib: url_for('contributions.display_contribution', contrib, _external=True))

    @post_dump
    def _transform(self, data, **kwargs):
        if contribution_type := data.pop('contribution_type', None):
            data['type_format'] = contribution_type
        if desc := data['_data'].get('description'):
            data['_data']['description'] = strip_tags(desc).strip()
        return data


class SubContributionRecordSchema(RecordSchema, SubContributionSchema):
    class Meta:
        model = SubContribution
        indexable = ('title', 'description', 'persons', 'location')
        non_indexable = ('subcontribution_id', 'type', 'event_id', 'contribution_id', 'category_id', 'category_path',
                         'url', 'start_dt', 'end_dt', 'duration')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda subc: SubContributionSchema(
        only=SubContributionRecordSchema.Meta.indexable
    ).dump(subc))
    category_path = fields.Function(lambda subc, ctx: _get_category_chain(subc.event, ctx.get('categories')))
    url = mm.Function(lambda subc: url_for('contributions.display_subcontribution', subc, _external=True))

    @post_dump
    def _transform(self, data, **kwargs):
        if desc := data['_data'].get('description'):
            data['_data']['description'] = strip_tags(desc).strip()
        return data


class _EventNoteDataSchema(EventNoteSchema):
    class Meta:
        fields = ('title', 'content', 'user')

    @post_dump
    def _transform(self, data, **kwargs):
        if desc := data.get('content'):
            data['content'] = strip_tags(desc).strip()
        if user := data.pop('user', None):
            data['persons'] = user
        return data


class EventNoteRecordSchema(RecordSchema, EventNoteSchema):
    class Meta:
        model = EventNote
        non_indexable = ('note_id', 'type', 'event_id', 'contribution_id', 'subcontribution_id', 'category_id',
                         'category_path', 'url', 'modified_dt')
        fields = RecordSchema.Meta.fields + non_indexable

    _data = fields.Function(lambda note: _EventNoteDataSchema().dump(note))
    category_path = fields.Function(lambda note, ctx: _get_category_chain(note.event, ctx.get('categories')))
    url = mm.Function(lambda note: url_for('event_notes.view', note, _external=True))
