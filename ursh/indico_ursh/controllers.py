# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
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

import posixpath

from flask_pluginengine import render_plugin_template

from indico.core.config import config
from indico.modules.events.management.controllers import RHManageEventBase
from indico.web.rh import RH
from indico.web.util import jsonify, jsonify_template

from flask import jsonify, request
from indico_ursh import _
from indico_ursh.util import register_shortcut, request_short_url, strip_end
from indico_ursh.views import WPShortenURLPage
from werkzeug.exceptions import BadRequest
from werkzeug.urls import url_parse


class RHGetShortURL(RH):
    """Make a request to the URL shortening service"""

    @staticmethod
    def _resolve_full_url(original_url):
        if url_parse(original_url).host:
            return original_url
        original_url = original_url.lstrip('/')
        return posixpath.join(config.BASE_URL, original_url)

    @staticmethod
    def _check_host(full_url):
        if url_parse(full_url).host != url_parse(config.BASE_URL).host:
            raise BadRequest('Invalid host for URL shortening service')

    def _process(self):
        original_url = request.json.get('original_url')
        full_url = self._resolve_full_url(original_url)
        self._check_host(full_url)
        short_url = request_short_url(full_url)
        return jsonify(url=short_url)


class RHShortURLPage(RH):
    """Provide a simple page, where users can submit a URL to be shortened"""

    def _process(self):
        return WPShortenURLPage.render_template('ursh_shortener_page.html')


class RHCustomShortURLPage(RHManageEventBase):
    """Provide a simple page, where users can submit a URL to be shortened"""

    def _make_absolute_url(self, url):
        return posixpath.join(config.BASE_URL, url[1:]) if url.startswith('/') else url

    def _get_error_msg(self, response):
        if response['status'] == 403:
            return _('Shortcut already exists')

    def _process_args(self):
        from indico_ursh.plugin import UrshPlugin
        super(RHCustomShortURLPage, self)._process_args()
        api_host = url_parse(UrshPlugin.settings.get('api_host'))
        self.ursh_host = strip_end(api_host.to_url(), api_host.path[1:])

    def _process_GET(self):
        original_url = self._make_absolute_url(request.args['original_url'])
        return WPShortenURLPage.render_template('ursh_custom_shortener_page.html',
                                                event=self.event,
                                                ursh_host=self.ursh_host,
                                                original_url=original_url)

    def _process_POST(self):
        original_url = self._make_absolute_url(request.args['original_url'])
        shortcut = request.form['shortcut']
        result = register_shortcut(original_url, shortcut)

        error = result.get('error')
        kwargs = {'success': True} if not error else {'success': False, 'msg': self._get_error_msg(result)}

        return jsonify_template('ursh_custom_shortener_page.html', render_plugin_template,
                                event=self.event, ursh_host=self.ursh_host, shortcut=shortcut,
                                original_url=original_url, **kwargs)
