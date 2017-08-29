# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import ast
import os
import shutil
import sys
from datetime import date

from flask import current_app
from werkzeug.security import safe_join
from xrootdpyfs import XRootDPyFS

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.core.storage import Storage, StorageError
from indico.util.string import return_ascii
from indico.web.flask.util import send_file


class XRootDStoragePlugin(IndicoPlugin):
    """XRootD Storage

    Provides XRootD/EOS storage backends.
    """

    def init(self):
        super(XRootDStoragePlugin, self).init()
        self.connect(signals.get_storage_backends, self._get_storage_backends)

    def _get_storage_backends(self, sender, **kwargs):
        yield XRootDStorage
        yield EOSStorage


class XRootDStorage(Storage):
    name = 'xrootd'
    simple_data = False

    def __init__(self, data):
        data = self._parse_data(data)
        self.xrootd_host = data['host']
        self.xrootd_opts = data.get('opts', '')
        self.path = data['root']
        self.fuse = bool(ast.literal_eval(data.get('fuse', 'False').title()))
        self.datestamp = bool(ast.literal_eval(data.get('datestamp', 'False').title()))

    @return_ascii
    def __repr__(self):
        qs = '?{}'.format(self.xrootd_opts) if self.xrootd_opts else ''
        return '<{}: root://{}/{}{}>'.format(type(self).__name__, self.xrootd_host, self.path, qs)

    def _get_xrootd_fs_uri(self):
        uri = 'root://{}//'.format(self.xrootd_host)
        if self.xrootd_opts:
            uri += '?' + self.xrootd_opts
        return uri

    def _get_xrootd_fs(self):
        return XRootDPyFS(self._get_xrootd_fs_uri())

    def _resolve_path(self, path):
        full_path = safe_join(self.path, path)
        if full_path is None:
            raise ValueError('Invalid path: {}'.format(path))
        return full_path

    def open(self, file_id):
        try:
            return self._get_xrootd_fs().open(self._resolve_path(file_id), 'rb')
        except Exception as e:
            raise StorageError('Could not open "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def _save(self, name, fileobj, fs):
        if self.datestamp:
            name = os.path.join(date.today().strftime('%Y%m'), name)
        filepath = self._resolve_path(name)
        if fs.exists(filepath):
            raise ValueError('A file with this name already exists')
        fileobj = self._ensure_fileobj(fileobj)
        basedir = os.path.dirname(filepath)
        if not fs.exists(basedir):
            fs.makedir(basedir, recursive=True, allow_recreate=True)
        with fs.open(filepath, 'wb') as f:
            checksum = self._copy_file(fileobj, f)
        return name, checksum

    def save(self, name, content_type, filename, fileobj):
        try:
            fs = self._get_xrootd_fs()
            return self._save(name, fileobj, fs)
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]

    def delete(self, file_id):
        try:
            self._get_xrootd_fs().remove(self._resolve_path(file_id))
        except Exception as e:
            raise StorageError('Could not delete "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def getsize(self, file_id):
        try:
            fs = self._get_xrootd_fs()
            path = self._resolve_path(file_id)
            fullpath = fs._p(path)
            status, stat = fs._client.stat(fullpath)
            if not status.ok:
                fs._raise_status(path, status)
            return stat.size
        except Exception as e:
            raise StorageError('Could not get size of "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def send_file(self, file_id, content_type, filename, inline=True):
        file_data = self._resolve_path(file_id) if self.fuse else self.open(file_id)
        return send_file(filename, file_data, content_type, inline=inline)


class EOSStorage(XRootDStorage):
    name = 'eos'

    def _get_xrootd_fs(self, size=None):
        query = {}
        if size is not None:
            query['eos.bookingsize'] = size
        return XRootDPyFS(self._get_xrootd_fs_uri(), query=query)

    def save(self, name, content_type, filename, fileobj):
        try:
            if isinstance(fileobj, basestring):
                size_hint = len(fileobj)
            elif hasattr(fileobj, 'seek') and hasattr(fileobj, 'tell'):
                pos = fileobj.tell()
                fileobj.seek(0, os.SEEK_END)
                size_hint = fileobj.tell() - pos
                fileobj.seek(pos, os.SEEK_SET)
            else:
                # Very unlikely to happen:
                # - strings/bytes have a length
                # - uploaded files are either fdopen (file-buffered) or BytesIO objects (-> seekable)
                # - other file-like objects are usually seekable too
                # So the only case where we can end up here is when using some custom file-like
                # object which does not have seek/tell methods.
                size_hint = current_app.config['MAX_CONTENT_LENGTH'] if current_app else None
            fs = self._get_xrootd_fs(size=size_hint)
            return self._save(name, fileobj, fs)
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]
