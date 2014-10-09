from indico_piwik.piwik import PiwikRequest


class PiwikQueryBase(object):
    """Base Piwik query"""

    def __init__(self, query_script):
        from indico_piwik import PiwikPlugin
        self.request = PiwikRequest(server_url=PiwikPlugin.settings.get('server_api_url'),
                                    site_id=PiwikPlugin.settings.get('site_id_events'),
                                    query_script=query_script)

    def call(self, **query_params):
        return self.request.call(**query_params)


class PiwikQueryReportBase(PiwikQueryBase):
    """Base Piwik query to request reports"""

    def __init__(self):
        from indico_piwik import PiwikPlugin
        super(PiwikQueryReportBase, self).__init__(query_script=PiwikPlugin.report_script)

    def call(self, date=('last7',), period='day', **query_params):
        date = ','.join(map(unicode, date))
        query_params.update(self.get_type_params)
        return super(PiwikQueryReportBase, self).call(date=date, period=period, **query_params)


class PiwikQueryReportEventBase(PiwikQueryReportBase):
    """Base Piwik query to request reports of events and contributions"""

    def __init__(self, event_id, start_date, end_date, contrib_id=None):
        super(PiwikQueryReportEventBase, self).__init__()
        self.event_id = event_id
        self.contrib_id = contrib_id
        self.start_date = start_date
        self.end_date = end_date

    def call(self, **query_params):
        return super(PiwikQueryReportEventBase, self).call(module='API', date=[self.start_date, self.end_date],
                                                           segmentation=self.get_segmentation(), **query_params)

    def get_segmentation(self):
        segmentation = {'customVariablePageName1': ('==', 'Conference'),
                        'customVariablePageValue1': ('==', self.event_id)}
        if self.contrib_id:
            segmentation['customVariablePageName2'] = ('==', 'Contribution')
            segmentation['customVariablePageValue2'] = ('==', self.contrib_id)

        segments = set()
        for name, (equality, value) in segmentation.iteritems():
            if isinstance(value, list):
                value = ','.join(value)
            segment = '{}{}{}'.format(name, equality, value)
            segments.add(segment)

        return ';'.join(segments)
