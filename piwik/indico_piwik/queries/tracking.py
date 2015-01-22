# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from indico_piwik.queries.base import PiwikQueryBase


class PiwikQueryTrackBase(PiwikQueryBase):
    """Base class for action-tracking queries"""

    def __init__(self):
        from indico_piwik.plugin import PiwikPlugin
        super(PiwikQueryTrackBase, self).__init__(query_script=PiwikPlugin.track_script)

    def call(self, action_url, action_name, **query_params):
        """Track an action in Piwik"""
        dt = datetime.now()
        query_params.update({'h': dt.hour, 'm': dt.minute, 's': dt.second})
        super(PiwikQueryTrackBase, self).call(idsite=self.request.site_id, rec=1, url=quote(action_url),
                                              action_name=quote(action_name), **query_params)


class PiwikQueryTrackDownload(PiwikQueryTrackBase):
    def call(self, download_url, download_title):
        """Track a download in Piwik"""
        if not download_url:
            raise ValueError("download_url can't be empty")
        if not download_title:
            raise ValueError("download_title can't be empty")
        super(PiwikQueryTrackDownload, self).call(action_url=download_url, action_name=download_title,
                                                  download=quote(download_url))
