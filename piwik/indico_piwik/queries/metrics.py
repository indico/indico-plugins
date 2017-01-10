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

from __future__ import division

from operator import itemgetter
from urllib2 import quote

from indico_piwik.queries.base import PiwikQueryReportEventBase
from indico_piwik.queries.utils import get_json_from_remote_server, reduce_json, stringify_seconds


class PiwikQueryReportEventMetricBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving metrics in JSON format"""

    def call(self, method, **query_params):
        return super(PiwikQueryReportEventMetricBase, self).call(method=method, format='JSON', **query_params)

    def get_result(self):
        """Perform the call and return the sum of all unique values"""
        pass


class PiwikQueryReportEventMetricVisitsBase(PiwikQueryReportEventMetricBase):
    def get_result(self, reduced=True):
        result = get_json_from_remote_server(self.call)
        if reduced:
            return int(reduce_json(result)) if result else 0
        return result if result else {}


class PiwikQueryReportEventMetricDownloads(PiwikQueryReportEventMetricBase):
    def call(self, download_url, **query_params):
        return super(PiwikQueryReportEventMetricDownloads, self).call(method='Actions.getDownload',
                                                                      downloadUrl=quote(download_url),
                                                                      **query_params)

    def get_result(self, download_url):
        result = get_json_from_remote_server(self.call, download_url=download_url, segmentation_enabled=False)
        return {'cumulative': self._get_cumulative_results(result),
                'individual': self._get_per_day_results(result)}

    def _get_per_day_results(self, results):
        hits_calendar = {}

        for date, hits in results.iteritems():
            day_hits = {'total': 0, 'unique': 0}
            if hits:
                for metrics in hits:
                    day_hits['total'] += metrics['nb_hits']
                    day_hits['unique'] += metrics['nb_uniq_visitors']
            hits_calendar[date] = day_hits

        return hits_calendar

    def _get_cumulative_results(self, results):
        """
        Returns a dictionary of {'total': x, 'unique': y} for the
        date range.
        """
        hits = {'total': 0, 'unique': 0}

        day_hits = list(hits[0] for hits in results.values() if hits)
        for metrics in day_hits:
            hits['total'] += metrics['nb_hits']
            hits['unique'] += metrics['nb_uniq_visitors']

        return hits


class PiwikQueryReportEventMetricReferrers(PiwikQueryReportEventMetricBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventMetricReferrers, self).call(method='Referrers.getReferrerType',
                                                                      period='range', **query_params)

    def get_result(self):
        """Perform the call and return a list of referrers"""
        result = get_json_from_remote_server(self.call)
        referrers = list(result)
        for referrer in referrers:
            referrer['sum_visit_length'] = stringify_seconds(referrer['sum_visit_length'])
        return sorted(referrers, key=itemgetter('nb_visits'), reverse=True)[0:10]


class PiwikQueryReportEventMetricUniqueVisits(PiwikQueryReportEventMetricVisitsBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventMetricUniqueVisits, self).call(method='VisitsSummary.getUniqueVisitors',
                                                                         **query_params)


class PiwikQueryReportEventMetricVisits(PiwikQueryReportEventMetricVisitsBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventMetricVisits, self).call(method='VisitsSummary.getVisits', **query_params)


class PiwikQueryReportEventMetricVisitDuration(PiwikQueryReportEventMetricBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventMetricVisitDuration, self).call(method='VisitsSummary.get', **query_params)

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
    def call(self, **query_params):
        return super(PiwikQueryReportEventMetricPeakDateAndVisitors, self).call(method='VisitsSummary.getVisits',
                                                                                **query_params)

    def get_result(self):
        """Perform the call and return the peak date and how many users"""
        result = get_json_from_remote_server(self.call)
        if result:
            date, value = max(result.iteritems(), key=itemgetter(1))
            return {'date': date, 'users': value}
        else:
            return {'date': "No Data", 'users': 0}
