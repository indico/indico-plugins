from __future__ import division

from operator import attrgetter, itemgetter

from . import PiwikQueryReportEventBase
from .utils import get_json_from_remote_server, reduce_json, stringify_seconds


class PiwikQueryReportEventMetricBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving metrics in JSON format"""

    def call(self, method, apiModule, **query_params):
        return super(PiwikQueryReportEventMetricBase, self).call(method=method, apiModule=apiModule,
                                                                 format='JSON', **query_params)

    def get_result(self, return_json=False):
        """Perform the call and return the sum of all unique values"""
        result = get_json_from_remote_server(self.call)
        if not result:
            return 0
        return result if return_json else int(reduce_json(result))


class PiwikQueryReportEventMetricReferrers(PiwikQueryReportEventMetricBase):
    def call(self):
        return super(PiwikQueryReportEventMetricReferrers, self).call(method='Referrers.getReferrerType',
                                                                      period='range')

    def get_result(self):
        """Perform the call and return a list of referrers"""
        result = get_json_from_remote_server(self.call)
        referrers = list(result)
        for referrer in referrers:
            referrer['sum_visit_length'] = stringify_seconds(referrer['sum_visit_length'])
        return sorted(referrers, key=attrgetter('nb_visits'), reverse=True)[0:10]


class PiwikQueryReportEventMetricUniqueVisits(PiwikQueryReportEventMetricBase):
    def call(self):
        return super(PiwikQueryReportEventMetricUniqueVisits, self).call(method='VisitsSummary.getUniqueVisitors')


class PiwikQueryReportEventMetricVisits(PiwikQueryReportEventMetricBase):
    def call(self):
        return super(PiwikQueryReportEventMetricVisits, self).call(method='VisitsSummary.getVisits')


class PiwikQueryReportEventMetricVisitDuration(PiwikQueryReportEventMetricBase):
    def call(self):
        return super(PiwikQueryReportEventMetricVisitDuration, self).call(method='VisitsSummary.get')

    def get_result(self):
        """Perform the call and return a string with the time in hh:mm:ss"""
        result = get_json_from_remote_server(self.call)
        seconds = self._get_average_duration(result) if result else 0
        return stringify_seconds(seconds)

    def _get_average_duration(self, result):
        seconds = 0
        data = result.values()
        if not data:
            return seconds
        for day in data:
            if isinstance(day, dict):
                seconds += day.get('avg_time_on_site', 0)
        return seconds / len(data)


class PiwikQueryReportEventMetricPeakDateAndVisitors(PiwikQueryReportEventMetricBase):
    def call(self):
        return super(PiwikQueryReportEventMetricPeakDateAndVisitors, self).call(method='VisitsSummary.getVisits')

    def get_result(self):
        """Perform the call and return the peak date and how many users"""
        result = get_json_from_remote_server(self.call)
        if result:
            date, value = max(result.iteritems(), key=itemgetter(1))
            return {'date': date, 'users': value}
        else:
            return {'date': "No Data", 'users': 0}
