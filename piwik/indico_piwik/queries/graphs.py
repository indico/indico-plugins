from base64 import b64encode

from . import PiwikQueryReportEventBase


class PiwikQueryEventGraphBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving PNG graphs"""

    def call(self, apiModule, apiAction, height=None, width=None, graphType='verticalBar', **query_params):
        if height is not None:
            query_params['height'] = height
        if width is not None:
            query_params['width'] = width
        return super(PiwikQueryEventGraphBase, self).call(method='ImageGraph.get',
                                                          apiModule=apiModule, apiAction=apiAction,
                                                          aliasedGraph='1', graphType=graphType, **query_params)

    def get_result(self):
        """Perform the call and return the graph data

        :return: Encoded PNG graph data string to be inserted in a `src`
                 atribute of a HTML img tag.
        """
        img_prefix = 'data:image/png;base64,'
        png = self.call(default_response='none')
        if png == 'none':
            return png
        img_code = b64encode(png)
        return img_prefix + img_code


class PiwikQueryEventGraphVisits(PiwikQueryEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryEventGraphVisits, self).call(apiModule='VisitsSummary', apiAction='get', width=720,
                                                            height=260, graphType='evolution', **query_params)


class PiwikQueryEventGraphDevices(PiwikQueryEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryEventGraphDevices, self).call(apiModule='UserSettings', apiAction='getOS',
                                                             period='range', width=320, height=260,
                                                             graphType='horizontalBar', **query_params)


class PiwikQueryEventGraphCountries(PiwikQueryEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryEventGraphCountries, self).call(apiModule='UserCountry', apiAction='getCountry',
                                                               period='range', width=490, height=260,
                                                               graphType='horizontalBar', **query_params)
