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

from flask import jsonify, request
from werkzeug.exceptions import BadRequest
from werkzeug.urls import url_parse

from indico.core.config import config
from indico.web.rh import RH

from indico_ursh.util import request_short_url
from indico_ursh.views import WPShortenURLPage


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


class RHDisplayShortenURLPage(RH):
    """Provide a simple page, where users can submit a URL to be shortened"""

    def _process(self):
        return WPShortenURLPage.render_template('url_shortener.html')
