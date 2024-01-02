# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico_piwik.piwik import PiwikRequest


class PiwikQueryBase:
    """Base Piwik query"""

    def __init__(self, query_script):
        from indico_piwik.plugin import PiwikPlugin
        self.request = PiwikRequest(server_url=PiwikPlugin.settings.get('server_api_url'),
                                    site_id=PiwikPlugin.settings.get('site_id_events'),
                                    api_token=PiwikPlugin.settings.get('server_token'),
                                    query_script=query_script)

    def call(self, **query_params):
        return self.request.call(**query_params)


class PiwikQueryReportBase(PiwikQueryBase):
    """Base Piwik query to request reports"""

    def __init__(self):
        from indico_piwik.plugin import PiwikPlugin
        super().__init__(query_script=PiwikPlugin.report_script)

    def call(self, date=('last7',), period='day', **query_params):
        date = ','.join(map(str, date))
        return super().call(date=date, period=period, **query_params)


class PiwikQueryReportEventBase(PiwikQueryReportBase):
    """Base Piwik query to request reports of events and contributions"""

    def __init__(self, event_id, start_date, end_date, contrib_id=None):
        super().__init__()
        self.event_id = event_id
        self.contrib_id = contrib_id
        self.start_date = start_date
        self.end_date = end_date

    def call(self, segmentation_enabled=True, **query_params):
        if segmentation_enabled:
            query_params['segment'] = self.get_segmentation()
        return super().call(module='API', date=[self.start_date, self.end_date], **query_params)

    def get_segmentation(self):
        segmentation = {'customVariablePageName1': ('==', 'Conference'),
                        'customVariablePageValue1': ('==', self.event_id)}

        if self.contrib_id:
            segmentation['customVariablePageName2'] = ('==', 'Contribution')
            segmentation['customVariablePageValue2'] = ('==', self.contrib_id)

        segments = set()
        for name, (equality, value) in segmentation.items():
            segment = f'{name}{equality}{value}'
            segments.add(segment)

        return ';'.join(segments)
