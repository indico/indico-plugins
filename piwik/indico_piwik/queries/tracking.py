# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
