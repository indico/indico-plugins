from datetime import datetime
from urllib2 import quote

from . import PiwikQueryBase


class PiwikQueryTrackBase(PiwikQueryBase):
    """Base class for action-tracking queries"""

    def __init__(self):
        from indico_piwik import PiwikPlugin
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
