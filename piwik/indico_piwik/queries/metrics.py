from __future__ import division

from operator import attrgetter, itemgetter
from urllib2 import quote

from . import PiwikQueryReportEventBase
from .utils import get_json_from_remote_server, reduce_json, stringify_seconds


class PiwikQueryReportEventMetricBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving metrics in JSON format"""

    def call(self, method, **query_params):
        return super(PiwikQueryReportEventMetricBase, self).call(method=method, format='JSON', **query_params)

    def get_result(self, return_json=False):
        """Perform the call and return the sum of all unique values"""
        result = get_json_from_remote_server(self.call)
        if not result:
            return 0
        return result if return_json else int(reduce_json(result))


class PiwikQueryReportEventMetricDownloads(PiwikQueryReportEventMetricBase):
    def call(self, download_url):
        return super(PiwikQueryReportEventMetricReferrers, self).call(method='Actions.getDownload',
                                                                      downloadUrl=quote(download_url))

    def get_result(self, download_url):
        result = get_json_from_remote_server(self.call, download_url=download_url)
        return {'cumulative': self._get_cumulative_results(result),
                'individual': self._get_per_day_results(result)}

    def _get_per_day_results(self, results):
        hits_calendar = {}

        # Piwik returns hits as a list of hits per date.
        for date, hits in results.iteritems():
            day_hits = {'total_hits': 0, 'unique_hits': 0}
            if hits:
                for metrics in hits:
                    day_hits['total_hits'] += metrics['nb_hits']
                    day_hits['unique_hits'] += metrics['nb_uniq_visitors']
            hits_calendar[date] = day_hits

        return hits_calendar

    def _get_cumulative_results(self, results):
        """
        Returns a dictionary of {'total_hits': x, 'unique_hits': y} for the
        date range.
        """
        total_hits = {'total_hits': 0, 'unique_hits': 0}

        day_hits = list(hits[0] for hits in results.values() if hits)
        for metrics in day_hits:
            total_hits['total_hits'] += metrics['nb_hits']
            total_hits['unique_hits'] += metrics['nb_uniq_visitors']

        return total_hits


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
