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

from datetime import datetime
from urllib2 import quote

from indico.core.celery import celery

from indico_piwik.piwik import PiwikRequest


@celery.task
def track_download_request(download_url, download_title):
    """Track a download in Piwik"""
    from indico_piwik.plugin import PiwikPlugin

    if not download_url:
        raise ValueError("download_url can't be empty")
    if not download_title:
        raise ValueError("download_title can't be empty")

    request = PiwikRequest(server_url=PiwikPlugin.settings.get('server_api_url'),
                           site_id=PiwikPlugin.settings.get('site_id_events'),
                           api_token=PiwikPlugin.settings.get('server_token'),
                           query_script=PiwikPlugin.track_script)

    action_url = quote(download_url)
    dt = datetime.now()
    request.call(idsite=request.site_id,
                 rec=1,
                 action_name=quote(download_title.encode('utf-8')),
                 url=action_url,
                 download=action_url,
                 h=dt.hour, m=dt.minute, s=dt.second)
