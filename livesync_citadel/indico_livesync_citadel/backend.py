# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import asyncio
from concurrent.futures.thread import ThreadPoolExecutor

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from werkzeug.urls import url_join

from indico.modules.attachments import Attachment
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote

from indico_livesync import LiveSyncBackendBase, SimpleChange, Uploader
from indico_livesync_citadel.models.search_id_map import EntryType, LiveSyncCitadelSearchAppIdMap
from indico_livesync_citadel.schemas import (EventRecordSchema, ContributionRecordSchema, AttachmentRecordSchema,
                                             SubContributionRecordSchema, EventNoteRecordSchema)


class LiveSyncCitadelUploader(Uploader):
    UPLOAD_BATCH_SIZE = 100

    def __init__(self, *args, **kwargs):
        from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin

        super().__init__(*args, **kwargs)

        self.schemas = {
            'event': EventRecordSchema(),
            'contribution': ContributionRecordSchema(),
            'subcontribution': SubContributionRecordSchema(),
            'attachment': AttachmentRecordSchema(),
            'note': EventNoteRecordSchema()
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

    def upload_jsondata(self, session, jsondata, change_type, obj_id, entry_type):
        response = None
        if change_type & SimpleChange.created:
            response = session.post(self.endpoint_url, json=jsondata)
        else:
            search_id = LiveSyncCitadelSearchAppIdMap.get_search_id(obj_id, entry_type)
            if not search_id:
                raise Exception('SearchMapId does not exist for the object')

            if change_type & SimpleChange.updated:
                url = url_join(self.search_app, 'api/record/{}'.format(search_id))
                response = session.put(url, json=jsondata)
            elif change_type & SimpleChange.deleted:
                url = url_join(self.search_app, 'api/record/{}'.format(search_id))
                response = session.delete(url, json=jsondata)

        if not response.ok:
            raise Exception('{} - {}'.format(response.status_code, response.text))
        elif change_type & SimpleChange.created:
            content = response.json()
            if content['metadata']['control_number']:
                LiveSyncCitadelSearchAppIdMap.create(content['metadata']['control_number'], obj_id, entry_type)
            else:
                raise Exception('Cannot create the search id mapping: {} - {}'
                                .format(response.status_code, response.text))

    def upload_records(self, records, from_queue):
        session = requests.Session()
        retry = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=1,
            status_forcelist=(x for x in (408, 429, 444, 449, 500, 502, 503, 504, 509)),
        )
        session.mount(self.search_app, HTTPAdapter(max_retries=retry))
        session.headers = self.headers
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor()
        tasks = []
        for idx, entry in enumerate(records):
            change = records[entry] if from_queue else SimpleChange.created
            jsondata, entry_type = self.get_jsondata(entry)
            if jsondata is None:
                continue

            def run(app, *args):
                with app.app_context():
                    self.upload_jsondata(*args)

            tasks.append(loop.run_in_executor(
                executor, run, current_app._get_current_object(), session, jsondata, change, entry.id, entry_type
            ))
            if len(tasks) >= LiveSyncCitadelUploader.UPLOAD_BATCH_SIZE or idx + 1 == len(records):
                loop.run_until_complete(asyncio.gather(*tasks))
                self.logger.info('Uploaded %d %s records', len(tasks), entry_type)
                tasks = []


class LiveSyncCitadelBackend(LiveSyncBackendBase):
    """LiveSync Citadel

    This backend uploads data to CERN-search.
    """

    uploader = LiveSyncCitadelUploader
