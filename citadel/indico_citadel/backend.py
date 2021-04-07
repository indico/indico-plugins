# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from functools import cached_property

import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import select
from urllib3 import Retry
from werkzeug.urls import url_join

from indico.core.db import db
from indico.modules.categories import Category

from indico_citadel.models.search_id_map import CitadelSearchAppIdMap, get_entry_type
from indico_citadel.schemas import (AttachmentRecordSchema, ContributionRecordSchema, EventNoteRecordSchema,
                                    EventRecordSchema, SubContributionRecordSchema)
from indico_citadel.util import parallelize
from indico_livesync import LiveSyncBackendBase, SimpleChange, Uploader


class LiveSyncCitadelUploader(Uploader):
    UPLOAD_BATCH_SIZE = 200

    def __init__(self, *args, **kwargs):
        from indico_citadel.plugin import CitadelPlugin

        super().__init__(*args, **kwargs)

        self.categories = None
        self.search_app = CitadelPlugin.settings.get('search_backend_url')
        self.endpoint_url = url_join(self.search_app, 'api/records/')
        self.headers = {
            'Authorization': 'Bearer {}'.format(CitadelPlugin.settings.get('search_backend_token'))
        }

    @cached_property
    def schemas(self):
        # this is a property because `self.categories` is only set to the cached data during an initial
        # export, and if we create the schemas earlier the context won't get the new data. and using the
        # property is cleaner than mutating `self.categories` after having passed it to the schemas...
        return [
            EventRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/events_v1.0.0.json')
            }),
            ContributionRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/contributions_v1.0.0.json')
            }),
            SubContributionRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/subcontributions_v1.0.0.json')
            }),
            AttachmentRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/attachments_v1.0.0.json')
            }),
            EventNoteRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/notes_v1.0.0.json')
            })
        ]

    def dump_record(self, obj):
        for schema in self.schemas:
            if isinstance(obj, schema.Meta.model):
                return schema.dump(obj)
        raise ValueError(f'unknown object ref: {obj}')

    def upload_record(self, entry, entries, session, from_queue):
        change_type = entries[entry] if from_queue else SimpleChange.created
        json = self.dump_record(entry)
        entry_type = get_entry_type(entry)
        response = None
        if change_type & SimpleChange.created:
            response = session.post(self.endpoint_url, json=json)
        else:
            search_id = CitadelSearchAppIdMap.get_search_id(entry.id, entry_type)
            if not search_id:
                raise Exception('SearchMapId does not exist for the object')

            if change_type & SimpleChange.updated:
                url = url_join(self.search_app, f'api/record/{search_id}')
                response = session.put(url, json=json)
            elif change_type & SimpleChange.deleted:
                url = url_join(self.search_app, f'api/record/{search_id}')
                response = session.delete(url, json=json)

        if not response.ok:
            raise Exception(f'{response.status_code} - {response.text} in record {json}')
        elif change_type & SimpleChange.created:
            content = response.json()
            control_number = content['metadata']['control_number']
            if control_number:
                CitadelSearchAppIdMap.create(control_number, entry.id, entry_type)
            else:
                raise Exception('Cannot create the search id mapping: {} - {}'
                                .format(response.status_code, response.text))
        response.close()

    def run_initial(self, events, total=None):
        cte = Category.get_tree_cte(lambda cat: db.func.json_build_object('id', cat.id, 'title', cat.title))
        self.categories = dict(db.session.execute(select([cte.c.id, cte.c.path])).fetchall())
        super().run_initial(events, total)

    def upload_records(self, records, from_queue):
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=30,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(['POST', 'PUT', 'DELETE'])
        )
        session.mount(self.search_app, HTTPAdapter(max_retries=retry))
        session.headers = self.headers
        uploader = parallelize(self.upload_record, entries=records)
        uploader(session, from_queue)


class LiveSyncCitadelBackend(LiveSyncBackendBase):
    """Citadel

    This backend uploads data to Citadel.
    """

    uploader = LiveSyncCitadelUploader
    unique = True
