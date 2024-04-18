# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from operator import itemgetter

from indico_piwik.queries.base import PiwikQueryReportEventBase
from indico_piwik.queries.utils import get_json_from_remote_server, reduce_json, stringify_seconds


class PiwikQueryReportEventMetricBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving metrics in JSON format"""

    def call(self, method, **query_params):
        return super().call(method=method, format='JSON', **query_params)

    def get_result(self):
        """Perform the call and return the sum of all unique values"""


class PiwikQueryReportEventMetricVisitsBase(PiwikQueryReportEventMetricBase):
    def get_result(self, reduced=True):
        result = get_json_from_remote_server(self.call)
        if reduced:
            return int(reduce_json(result)) if result else 0
        return result or {}


class PiwikQueryReportEventMetricReferrers(PiwikQueryReportEventMetricBase):
    def call(self, **query_params):
        return super().call(method='Referrers.getReferrerType', period='range', **query_params)

    def get_result(self):
        """Perform the call and return a list of referrers"""
        result = get_json_from_remote_server(self.call)
        referrers = list(result)
        for referrer in referrers:
            referrer['sum_visit_length'] = stringify_seconds(referrer['sum_visit_length'])
        return sorted(referrers, key=itemgetter('nb_visits'), reverse=True)[0:10]


class PiwikQueryReportEventMetricUniqueVisits(PiwikQueryReportEventMetricVisitsBase):
    def call(self, **query_params):
        return super().call(method='VisitsSummary.getUniqueVisitors', **query_params)


class PiwikQueryReportEventMetricVisits(PiwikQueryReportEventMetricVisitsBase):
    def call(self, **query_params):
        return super().call(method='VisitsSummary.getVisits', **query_params)


class PiwikQueryReportEventMetricVisitDuration(PiwikQueryReportEventMetricBase):
    def call(self, **query_params):
        return super().call(method='VisitsSummary.get', **query_params)

    def get_result(self):
        """Perform the call and return a string with the time in hh:mm:ss"""
        result = get_json_from_remote_server(self.call)
        seconds = self._get_average_duration(result) if result else 0
        return stringify_seconds(seconds)

    def _get_average_duration(self, result):
        seconds = 0
        data = list(result.values())
        if not data:
            return seconds
        for day in data:
            if isinstance(day, dict):
                seconds += day.get('avg_time_on_site', 0)
        return seconds / len(data)


class PiwikQueryReportEventMetricPeakDateAndVisitors(PiwikQueryReportEventMetricBase):
    def call(self, **query_params):
        return super().call(method='VisitsSummary.getVisits', **query_params)

    def get_result(self):
        """Perform the call and return the peak date and how many users"""
        result = get_json_from_remote_server(self.call)
        if result:
            date, value = max(result.items(), key=itemgetter(1))
            return {'date': date, 'users': value}
        else:
            return {'date': 'No Data', 'users': 0}
