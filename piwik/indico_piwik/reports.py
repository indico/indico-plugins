# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import joinedload

from indico.core.cache import make_scoped_cache
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.util.date_time import format_time, now_utc, utc_to_server

from indico_piwik.queries.graphs import PiwikQueryReportEventGraphCountries, PiwikQueryReportEventGraphDevices
from indico_piwik.queries.metrics import (PiwikQueryReportEventMetricPeakDateAndVisitors,
                                          PiwikQueryReportEventMetricReferrers, PiwikQueryReportEventMetricUniqueVisits,
                                          PiwikQueryReportEventMetricVisitDuration, PiwikQueryReportEventMetricVisits)


class ReportBase:
    """Wrapper for Piwik report collection"""

    serializable_fields = []
    default_report_interval = 14

    def __init__(self, event_id, contrib_id=None, start_date=None, end_date=None, **report_params):
        self.event_id = event_id
        self.contrib_id = contrib_id
        self._init_date_range(start_date, end_date)
        self.params = {'start_date': self.start_date,
                       'end_date': self.end_date,
                       'event_id': self.event_id,
                       'contrib_id': self.contrib_id}
        self._build_report(**report_params)
        self.timestamp = utc_to_server(now_utc())

    @property
    def event(self):
        return Event.get_or_404(self.event_id, is_deleted=False)

    @classmethod
    def get(cls, *args, **kwargs):
        """Create and return a serializable Report object, retrieved from cache if possible"""

        from indico_piwik.plugin import PiwikPlugin

        if not PiwikPlugin.settings.get('cache_enabled'):
            return cls(*args, **kwargs).serialize()

        cache = make_scoped_cache('piwik-report')
        key = f'{cls.__name__}-{args}-{kwargs}'

        report = cache.get(key)
        if not report:
            report = cls(*args, **kwargs)
            cache.set(key, report, timeout=PiwikPlugin.settings.get('cache_ttl'))
        return report.serialize()

    def _build_report(self):
        raise NotImplementedError

    def _init_date_range(self, start_date=None, end_date=None):
        """Set date range defaults if no dates are passed"""
        self.end_date = end_date
        self.start_date = start_date
        if self.end_date is None:
            today = now_utc().date()
            end_date = self.event.end_dt.date()
            self.end_date = min(today, end_date)
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=ReportBase.default_report_interval)

    def serialize(self):
        return {attr: getattr(self, attr) for attr in self.serializable_fields}


class ReportCountries(ReportBase):
    serializable_fields = ['graphs']

    def _build_report(self):
        self.graphs = {'countries': PiwikQueryReportEventGraphCountries(**self.params).get_result()}


class ReportDevices(ReportBase):
    serializable_fields = ['graphs']

    def _build_report(self):
        self.graphs = {'devices': PiwikQueryReportEventGraphDevices(**self.params).get_result()}


class ReportGeneral(ReportBase):
    serializable_fields = ['event_id', 'contrib_id', 'start_date', 'end_date', 'metrics', 'contributions', 'timestamp']

    def _build_report(self):
        """Build the report by performing queries to Piwik"""
        self.metrics = {}
        queries = {'visits': PiwikQueryReportEventMetricVisits(**self.params),
                   'unique_visits': PiwikQueryReportEventMetricUniqueVisits(**self.params),
                   'visit_duration': PiwikQueryReportEventMetricVisitDuration(**self.params),
                   'referrers': PiwikQueryReportEventMetricReferrers(**self.params),
                   'peak': PiwikQueryReportEventMetricPeakDateAndVisitors(**self.params)}

        for query_name, query in queries.items():
            self.metrics[query_name] = query.get_result()

        self._fetch_contribution_info()

    def _fetch_contribution_info(self):
        """Build the list of information entries for contributions of the event"""
        self.contributions = {}
        query = (Contribution.query
                 .with_parent(self.event)
                 .options(joinedload('legacy_mapping'),
                          joinedload('timetable_entry').lazyload('*')))
        for contribution in query:
            if not contribution.start_dt:
                continue
            cid = (contribution.legacy_mapping.legacy_contribution_id if contribution.legacy_mapping
                   else contribution.id)
            key = f'{contribution.event_id}t{cid}'
            self.contributions[key] = f'{contribution.title} ({format_time(contribution.start_dt)})'


class ReportVisitsPerDay(ReportBase):
    serializable_fields = ['metrics']

    def _build_report(self):
        self.metrics = {'unique': PiwikQueryReportEventMetricUniqueVisits(**self.params).get_result(reduced=False),
                        'total': PiwikQueryReportEventMetricVisits(**self.params).get_result(reduced=False)}
        self._reduce_metrics()

    def _reduce_metrics(self):
        reduced_metrics = defaultdict(dict)

        for metric_type, records in self.metrics.items():
            for date, hits in records.items():
                reduced_metrics[date][metric_type] = int(hits)

        self.metrics = reduced_metrics
