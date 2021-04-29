# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
from functools import cached_property
from operator import attrgetter
from pprint import pformat

import requests
from pygments import highlight
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.lexers.agile import Python3Lexer
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.attributes import flag_modified
from urllib3 import Retry
from werkzeug.urls import url_join

from indico.core.db import db
from indico.modules.attachments import Attachment
from indico.modules.attachments.models.attachments import AttachmentFile, AttachmentType
from indico.modules.categories import Category
from indico.util.console import cformat, verbose_iterator
from indico.util.string import strip_control_chars

from indico_citadel.models.id_map import CitadelIdMap, get_entry_type
from indico_citadel.schemas import (AttachmentRecordSchema, ContributionRecordSchema, EventNoteRecordSchema,
                                    EventRecordSchema, SubContributionRecordSchema)
from indico_citadel.util import parallelize
from indico_livesync import LiveSyncBackendBase, SimpleChange, Uploader


lexer = Python3Lexer()
formatter = Terminal256Formatter(style='native')


def _format_change_str(change):
    return ','.join(flag.name for flag in SimpleChange if change & flag)


def _print_record(record):
    obj_type, obj_id, data, changes = record
    print()  # verbose_iterator during initial exports doesn't end its line
    print(f'{_format_change_str(changes)}: {obj_type.name} {obj_id}')
    if data is not None:
        print(highlight(pformat(data), lexer, formatter))
    return record


class LiveSyncCitadelUploader(Uploader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.categories = None
        self.search_app = self.backend.plugin.settings.get('search_backend_url')
        self.endpoint_url = url_join(self.search_app, 'api/records/')
        self.headers = {
            'Authorization': 'Bearer {}'.format(self.backend.plugin.settings.get('search_backend_token'))
        }

    @cached_property
    def schemas(self):
        # this is a property because `self.categories` is only set to the cached data during an initial
        # export, and if we create the schemas earlier the context won't get the new data. and using the
        # property is cleaner than mutating `self.categories` after having passed it to the schemas...
        return [
            EventRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/events_v1.0.0.json'),
            }),
            ContributionRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/contributions_v1.0.0.json'),
            }),
            SubContributionRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/subcontributions_v1.0.0.json'),
            }),
            AttachmentRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/attachments_v1.0.0.json'),
            }),
            EventNoteRecordSchema(context={
                'categories': self.categories,
                'schema': url_join(self.search_app, 'schemas/indico/notes_v1.0.0.json'),
            })
        ]

    def dump_record(self, obj):
        for schema in self.schemas:
            if isinstance(obj, schema.Meta.model):
                return schema.dump(obj)
        raise ValueError(f'unknown object ref: {obj}')

    def _citadel_create(self, session, object_type, object_id, data):
        try:
            resp = session.post(self.endpoint_url, json=data)
            resp.raise_for_status()
        except RequestException as exc:
            if resp := exc.response:
                raise Exception(f'Could not create record on citadel: {resp.status_code}; {resp.text}; {data}')
            raise Exception(f'Could not create record on citadel: {exc}; {data}')
        response_data = resp.json()
        new_citadel_id = response_data['metadata']['control_number']
        try:
            CitadelIdMap.create(object_type, object_id, new_citadel_id)
        except IntegrityError:
            # if we already have a mapping entry, delete the newly created record and
            # update the existing one in case something changed in the meantime
            self.logger.error(f'{object_type.name.title()} %d already in citadel; deleting+updating', object_id)
            db.session.rollback()
            self._citadel_delete(session, new_citadel_id, delete_mapping=False)
            existing_citadel_id = CitadelIdMap.get_citadel_id(object_type, object_id)
            assert existing_citadel_id is not None
            self._citadel_update(session, existing_citadel_id, data)
        resp.close()

    def _citadel_update(self, session, citadel_id, data):
        try:
            resp = session.put(url_join(self.search_app, f'api/record/{citadel_id}'), json=data)
            resp.raise_for_status()
            resp.close()
        except RequestException as exc:
            if resp := exc.response:
                raise Exception(f'Could not update record {citadel_id} on citadel: '
                                f'{resp.status_code}; {resp.text}; {data}')
            raise Exception(f'Could not update record {citadel_id} on citadel: {exc}; {data}')

    def _citadel_delete(self, session, citadel_id, *, delete_mapping):
        try:
            resp = session.delete(url_join(self.search_app, f'api/record/{citadel_id}'))
            resp.raise_for_status()
            resp.close()
        except RequestException as exc:
            if resp := exc.response:
                raise Exception(f'Could not delete record {citadel_id} from citadel: {resp.status_code}; {resp.text}')
            raise Exception(f'Could not delete record {citadel_id} from citadel: {exc}')
        if delete_mapping:
            CitadelIdMap.query.filter_by(citadel_id=citadel_id).delete()
            db.session.commit()

    def upload_record(self, entry, session):
        object_type, object_id, data, change_type = entry

        if change_type & SimpleChange.created:
            self._citadel_create(session, object_type, object_id, data)
        elif change_type & SimpleChange.updated:
            citadel_id = CitadelIdMap.get_citadel_id(object_type, object_id)
            if citadel_id is None:
                raise Exception(f'Cannot update {object_type.name} {object_id}: No citadel ID found')
            self._citadel_update(session, citadel_id, data)
        elif change_type & SimpleChange.deleted:
            citadel_id = CitadelIdMap.get_citadel_id(object_type, object_id)
            if citadel_id is None:
                raise Exception(f'Cannot delete {object_type.name} {object_id}: No citadel ID found')
            self._citadel_delete(session, citadel_id, delete_mapping=True)

    def upload_file(self, entry, session):
        with entry.attachment.file.open() as file:
            resp = session.put(
                url_join(self.search_app, f'api/record/{entry.citadel_id}/files/attachment'),
                data=file
            )
        if resp.ok:
            entry.attachment_file_id = entry.attachment.file.id
            db.session.merge(entry)
            db.session.commit()
        else:
            self.logger.error('Failed uploading attachment %d: [%d] %s',
                              entry.attachment.id, resp.status_code, resp.text)

    def run_initial(self, events, total):
        cte = Category.get_tree_cte(lambda cat: db.func.json_build_object('id', cat.id, 'title', cat.title))
        self.categories = dict(db.session.execute(select([cte.c.id, cte.c.path])).fetchall())
        super().run_initial(events, total)

    def upload_records(self, records):
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=3,
            status_forcelist=[502, 503, 504],
            allowed_methods=frozenset(['POST', 'PUT', 'DELETE'])
        )
        session.mount(self.search_app, HTTPAdapter(max_retries=retry))
        session.headers = self.headers
        dumped_records = (
            (
                get_entry_type(rec), rec.id,
                self.dump_record(rec) if not change_type & SimpleChange.deleted else None,
                change_type
            ) for rec, change_type in records
        )

        if self.verbose:
            dumped_records = (_print_record(x) for x in dumped_records)

        uploader = parallelize(self.upload_record, entries=dumped_records)
        uploader(session)

    def upload_files(self, files):
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=3,
            status_forcelist=[502, 503, 504],
            allowed_methods=frozenset(['PUT'])
        )
        session.mount(self.search_app, HTTPAdapter(max_retries=retry))
        session.headers = self.headers
        uploader = parallelize(self.upload_file, entries=files, batch_size=100)
        uploader(session)


class LiveSyncCitadelBackend(LiveSyncBackendBase):
    """Citadel

    This backend uploads data to Citadel.
    """

    uploader = LiveSyncCitadelUploader
    unique = True
    reset_deletes_indexed_data = False

    def check_queue_status(self):
        allowed, reason = super().check_queue_status()
        if not allowed:
            return False, reason
        if not self.agent.settings.get('file_upload_done'):
            return False, 'file upload pending'
        return True, None

    def is_configured(self):
        return bool(self.plugin.settings.get('search_backend_url') and self.plugin.settings.get('search_backend_token'))

    def set_initial_file_upload_state(self, state):
        if self.agent.settings['file_upload_done'] == state:
            return
        self.plugin.logger.info('Initial file upload flag set to %s', state)
        self.agent.settings['file_upload_done'] = state
        flag_modified(self.agent, 'settings')

    def get_initial_query(self, model_cls, force):
        query = super().get_initial_query(model_cls, force)
        if not force:
            query = query.filter(~model_cls.citadel_id_mapping.has())
        return query

    def process_queue(self, uploader):
        super().process_queue(uploader)
        uploader_name = type(uploader).__name__
        self.plugin.logger.info(f'{uploader_name} starting file upload')
        total = self.run_export_files(verbose=False)
        self.plugin.logger.info(f'{uploader_name} finished uploading %d files', total)

    def run_initial_export(self, batch_size, force=False, verbose=False):
        super().run_initial_export(batch_size, force, verbose)
        print('Initial export finished')

        if self.get_initial_query(Attachment, force=True).has_rows():
            print('You need to export attachment contents as well')
            print(cformat('To do so, run %{yellow!}indico citadel upload%{reset}'))
        else:
            # no files -> mark file upload as done so queue runs are possible
            self.set_initial_file_upload_state(True)

    def run_export_files(self, batch=1000, force=False, max_size=None, verbose=True):
        from indico_citadel.plugin import CitadelPlugin

        if max_size is None:
            max_size = CitadelPlugin.settings.get('max_file_size')

        attachments = (
            CitadelIdMap.query
            .join(Attachment)
            .join(AttachmentFile, Attachment.file_id == AttachmentFile.id)
            .filter(Attachment.type == AttachmentType.file)
            .filter(AttachmentFile.size > 0, AttachmentFile.size <= max_size * 1024 * 1024)
            .filter(db.func.lower(AttachmentFile.extension).in_(
                [s.lower() for s in CitadelPlugin.settings.get('file_extensions')]
            ))
            .options(contains_eager(CitadelIdMap.attachment).contains_eager(Attachment.file))
        )
        if not force:
            attachments = attachments.filter(db.or_(CitadelIdMap.attachment_file_id.is_(None),
                                                    CitadelIdMap.attachment_file_id != Attachment.file_id))
        uploader = self.uploader(self)
        attachments = attachments.yield_per(batch)
        total = attachments.count()
        if verbose:
            attachments = verbose_iterator(attachments, total, attrgetter('id'),
                                           lambda obj: re.sub(r'\s+', ' ', strip_control_chars(obj.attachment.title)),
                                           print_total_time=True)
        uploader.upload_files(attachments)
        return total

    def check_reset_status(self):
        allowed, reason = super().check_reset_status()
        if not allowed:
            return False, reason
        if not self.is_configured():
            return False, 'Citadel is not properly configured.'
        if not CitadelIdMap.query.has_rows():
            return False, 'It looks like you did not export any data to Citadel yet so there is nothing to reset.'
        return True, None

    def reset(self):
        super().reset()
        self.set_initial_file_upload_state(False)
        CitadelIdMap.query.delete()
