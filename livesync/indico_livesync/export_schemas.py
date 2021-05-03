# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from marshmallow import fields

from indico.core.db.sqlalchemy.links import LinkType
from indico.core.marshmallow import mm
from indico.modules.attachments import Attachment
from indico.modules.categories import Category
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.search.base import SearchTarget
from indico.modules.search.schemas import LocationSchema, PersonSchema
from indico.util.marshmallow import NoneRemovingList
from indico.web.flask.util import url_for


class CategorySchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        fields = ('id', 'title', 'url')

    url = fields.Function(lambda c: url_for('categories.display', category_id=c['id']))


class AttachmentSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Attachment
        fields = ('attachment_id', 'folder_id', 'type', 'type_format', 'title', 'filename', 'event_id',
                  'contribution_id', 'subcontribution_id', 'user', 'url', 'category_id', 'category_path',
                  'modified_dt')

    attachment_id = fields.Int(attribute='id')
    folder_id = fields.Int(attribute='folder_id')
    type = fields.Constant(SearchTarget.attachment.name)
    type_format = fields.String(attribute='type.name')
    filename = fields.String(attribute='file.filename')
    event_id = fields.Int(attribute='folder.event.id')
    contribution_id = fields.Method('_contribution_id')
    subcontribution_id = fields.Int(attribute='folder.subcontribution_id')
    user = fields.Nested(PersonSchema)
    category_id = fields.Int(attribute='folder.event.category_id')
    category_path = fields.List(fields.Nested(CategorySchema), attribute='folder.event.detailed_category_chain')
    url = fields.String(attribute='download_url')

    def _contribution_id(self, attachment):
        if attachment.folder.link_type == LinkType.contribution:
            return attachment.folder.contribution_id
        elif attachment.folder.link_type == LinkType.subcontribution:
            return attachment.folder.subcontribution.contribution_id
        return None


class ContributionSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Contribution
        fields = ('contribution_id', 'type', 'type_format', 'event_id', 'title', 'description', 'location',
                  'persons', 'url', 'category_id', 'category_path', 'start_dt', 'end_dt', 'duration')

    contribution_id = fields.Int(attribute='id')
    type = fields.Constant(SearchTarget.contribution.name)
    type_format = fields.String(attribute='type.name')
    location = fields.Function(lambda contrib: LocationSchema().dump(contrib))
    persons = NoneRemovingList(fields.Nested(PersonSchema), attribute='person_links')
    category_id = fields.Int(attribute='event.category_id')
    category_path = fields.List(fields.Nested(CategorySchema), attribute='event.detailed_category_chain')
    url = fields.Function(lambda contrib: url_for('contributions.display_contribution', contrib, _external=False))
    duration = fields.TimeDelta(precision=fields.TimeDelta.MINUTES)


class SubContributionSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = SubContribution
        fields = ('subcontribution_id', 'type', 'title', 'description', 'event_id', 'contribution_id', 'persons',
                  'location', 'url', 'category_id', 'category_path', 'start_dt', 'end_dt', 'duration')

    subcontribution_id = fields.Int(attribute='id')
    type = fields.Constant(SearchTarget.subcontribution.name)
    event_id = fields.Int(attribute='contribution.event_id')
    persons = NoneRemovingList(fields.Nested(PersonSchema), attribute='person_links')
    location = fields.Function(lambda subc: LocationSchema().dump(subc.contribution))
    category_id = fields.Int(attribute='event.category_id')
    category_path = fields.List(fields.Nested(CategorySchema), attribute='event.detailed_category_chain')
    url = fields.Function(lambda subc: url_for('contributions.display_subcontribution', subc, _external=False))
    start_dt = fields.DateTime(attribute='contribution.start_dt')
    end_dt = fields.DateTime(attribute='contribution.end_dt')
    duration = fields.TimeDelta(precision=fields.TimeDelta.MINUTES)


class EventNoteSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = EventNote
        fields = ('note_id', 'type', 'content', 'event_id', 'contribution_id', 'subcontribution_id', 'url',
                  'category_id', 'category_path', 'modified_dt', 'user')

    note_id = fields.Int(attribute='id')
    type = fields.Constant(SearchTarget.event_note.name)
    content = fields.Str(attribute='current_revision.source')
    contribution_id = fields.Method('_contribution_id')
    subcontribution_id = fields.Int()
    category_id = fields.Int(attribute='event.category_id')
    category_path = fields.List(fields.Nested(CategorySchema), attribute='event.detailed_category_chain')
    url = fields.Function(lambda note: url_for('event_notes.view', note, _external=False))
    modified_dt = fields.DateTime(attribute='current_revision.created_dt')
    user = fields.Nested(PersonSchema, attribute='current_revision.user')

    def _contribution_id(self, note):
        if note.link_type == LinkType.contribution:
            return note.contribution_id
        elif note.link_type == LinkType.subcontribution:
            return note.subcontribution.contribution_id
