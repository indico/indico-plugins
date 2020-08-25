# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import requests
from werkzeug.urls import url_join

from indico.core.db import db
from indico.modules.attachments import Attachment
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote

from indico_livesync import LiveSyncBackendBase, SimpleChange, Uploader
from indico_livesync_citadel.models.search_id_map import EntryType, LiveSyncCitadelSearchAppIdMap
from indico_livesync_citadel.schemas import (AttachmentSchema, ContributionSchema, EventNoteSchema, EventSchema,
                                             SubContributionSchema)


class LiveSyncCitadelUploader(Uploader):
    def __init__(self, *args, **kwargs):
        from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin

        super(LiveSyncCitadelUploader, self).__init__(*args, **kwargs)

        self.schemas = {
            'event': EventSchema(),
            'contribution': ContributionSchema(),
            'subcontribution': SubContributionSchema(),
            'attachment': AttachmentSchema(),
            'note': EventNoteSchema()
        }
        self.search_app = LiveSyncCitadelPlugin.settings.get('search_backend_url')
        self.endpoint_url = url_join(self.search_app, 'api/records/')
        self.headers = {
            'Authorization': 'Bearer {}'.format(LiveSyncCitadelPlugin.settings.get('search_backend_token'))
        }

    def get_jsondata(self, obj):
        if isinstance(obj, Event):
            event_data = self.schemas['event'].dump(obj)
            event_data['$schema'] = url_join(self.search_app, 'schemas/indico/events_v1.0.0.json')
            return event_data, EntryType.event
        elif isinstance(obj, Contribution):
            contribution_data = self.schemas['contribution'].dump(obj)
            contribution_data['$schema'] = url_join(self.search_app, 'schemas/indico/contributions_v1.0.0.json')
            return contribution_data, EntryType.contribution
        elif isinstance(obj, SubContribution):
            subcontrib_data = self.schemas['subcontribution'].dump(obj)
            subcontrib_data['$schema'] = url_join(self.search_app, 'schemas/indico/subcontributions_v1.0.0.json')
            return subcontrib_data, EntryType.subcontribution
        elif isinstance(obj, Attachment):
            attachment_data = self.schemas['attachment'].dump(obj)
            attachment_data['$schema'] = url_join(self.search_app, 'schemas/indico/attachments_v1.0.0.json')
            return attachment_data, EntryType.attachment
        elif isinstance(obj, EventNote):
            note_data = self.schemas['note'].dump(obj)
            note_data['$schema'] = url_join(self.search_app, 'schemas/indico/notes_v1.0.0.json')
            return note_data, EntryType.note
        else:
            raise ValueError('unknown object ref: {}'.format(obj))

    def upload_jsondata(self, jsondata, change_type, obj_id, entry_type):
        response = None
        if change_type & SimpleChange.created:
            response = requests.post(self.endpoint_url, headers=self.headers, json=jsondata)
        else:
            search_id = LiveSyncCitadelSearchAppIdMap.get_search_id(obj_id, entry_type)
            if not search_id:
                raise Exception('SearchMapId does not exist for the object')

            if change_type & SimpleChange.updated:
                url = url_join(self.search_app, 'api/record/{}'.format(search_id))
                response = requests.put(url, headers=self.headers, json=jsondata)
            elif change_type & SimpleChange.deleted:
                url = url_join(self.search_app, 'api/record/{}'.format(search_id))
                response = requests.delete(url, headers=self.headers, json=jsondata)

        if not response.ok:
            raise Exception('{} - {}'.format(response.status_code, response.text))
        elif change_type & SimpleChange.created:
            content = response.json()
            if content['metadata']['control_number']:
                LiveSyncCitadelSearchAppIdMap.create(content['metadata']['control_number'], obj_id, entry_type)
                db.session.commit()
            else:
                raise Exception('Cannot create the search id mapping: {} - {}'
                                .format(response.status_code, response.text))

    def upload_records(self, records, from_queue):
        for entry in records:
            change = records[entry] if from_queue else SimpleChange.created
            jsondata, entry_type = self.get_jsondata(entry)
            if jsondata is not None:
                self.upload_jsondata(jsondata, change, entry.id, entry_type)


class LiveSyncCitadelBackend(LiveSyncBackendBase):
    """LiveSync Citadel

    This backend uploads data to CERN-search.
    """

    uploader = LiveSyncCitadelUploader
