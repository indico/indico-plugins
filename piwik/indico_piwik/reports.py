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

from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import joinedload

from indico.legacy.common.cache import GenericCache
from indico.modules.attachments.util import get_nested_attached_items
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.util.date_time import format_time, now_utc, utc_to_server
from indico.util.serializer import Serializer
from indico.util.string import to_unicode

from indico_piwik.queries.graphs import PiwikQueryReportEventGraphCountries, PiwikQueryReportEventGraphDevices
from indico_piwik.queries.metrics import (PiwikQueryReportEventMetricDownloads,
                                          PiwikQueryReportEventMetricPeakDateAndVisitors,
                                          PiwikQueryReportEventMetricReferrers, PiwikQueryReportEventMetricUniqueVisits,
                                          PiwikQueryReportEventMetricVisitDuration, PiwikQueryReportEventMetricVisits)


class ReportBase(Serializer):
    """Wrapper for Piwik report collection"""

    __public__ = []
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
        return Event.get_one(self.event_id, is_deleted=False)

    @classmethod
    def get(cls, *args, **kwargs):
        """Create and return a serializable Report object, retrieved from cache if possible"""

        from indico_piwik.plugin import PiwikPlugin

        if not PiwikPlugin.settings.get('cache_enabled'):
            return cls(*args, **kwargs).to_serializable()

        cache = GenericCache('Piwik.Report')
        key = u'{}-{}-{}'.format(cls.__name__, args, kwargs)

        report = cache.get(key)
        if not report:
            report = cls(*args, **kwargs)
            cache.set(key, report, PiwikPlugin.settings.get('cache_ttl'))
        return report.to_serializable()

    def _build_report(self):
        """To be overriden"""
        pass

    def _init_date_range(self, start_date=None, end_date=None):
        """Set date range defaults if no dates are passed"""
        self.end_date = end_date
        self.start_date = start_date
        if self.end_date is None:
            today = now_utc().date()
            end_date = self.event.end_dt.date()
            self.end_date = end_date if end_date < today else today
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=ReportBase.default_report_interval)


class ReportCountries(ReportBase):
    __public__ = ['graphs']

    def _build_report(self):
        self.graphs = {'countries': PiwikQueryReportEventGraphCountries(**self.params).get_result()}


class ReportDevices(ReportBase):
    __public__ = ['graphs']

    def _build_report(self):
        self.graphs = {'devices': PiwikQueryReportEventGraphDevices(**self.params).get_result()}


class ReportDownloads(ReportBase):
    __public__ = ['metrics']

    def _build_report(self, download_url):
        self.metrics = {'downloads': PiwikQueryReportEventMetricDownloads(**self.params).get_result(download_url)}


class ReportGeneral(ReportBase):
    __public__ = ['event_id', 'contrib_id', 'start_date', 'end_date', 'metrics', 'contributions', 'timestamp']

    def _build_report(self):
        """Build the report by performing queries to Piwik"""
        self.metrics = {}
        queries = {'visits': PiwikQueryReportEventMetricVisits(**self.params),
                   'unique_visits': PiwikQueryReportEventMetricUniqueVisits(**self.params),
                   'visit_duration': PiwikQueryReportEventMetricVisitDuration(**self.params),
                   'referrers': PiwikQueryReportEventMetricReferrers(**self.params),
                   'peak': PiwikQueryReportEventMetricPeakDateAndVisitors(**self.params)}

        for query_name, query in queries.iteritems():
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
            key = '{}t{}'.format(contribution.event_id, cid)
            self.contributions[key] = u'{} ({})'.format(contribution.title,
                                                        to_unicode(format_time(contribution.start_dt)))


class ReportMaterial(ReportBase):
    __public__ = ['material']

    def _build_report(self):
        event = Event.get_one(self.params['event_id'], is_deleted=False)
        new_material = get_nested_attached_items(event)
        self.material = {'tree': [self._format_data(new_material)]}

    def _format_data(self, raw_node):
        if 'object' not in raw_node:
            return None
        node = {'label': raw_node['object'].title,
                'children': []}
        if 'files' in raw_node:
            node['children'] += self._format_data_files(raw_node['files'])
        if 'folders' in raw_node:
            for folder in raw_node['folders']:
                node['children'] += [{'label': folder.title, 'children': self._format_data_files(folder.attachments)}]
        if 'children' in raw_node:
            node['children'] += [self._format_data(child) for child in raw_node['children']]
        if not node['children']:
            return None
        return node

    def _format_data_files(self, files):
        return [{'id': f.absolute_download_url, 'label': f.title} for f in files]


class ReportVisitsPerDay(ReportBase):
    __public__ = ['metrics']

    def _build_report(self):
        self.metrics = {'unique': PiwikQueryReportEventMetricUniqueVisits(**self.params).get_result(reduced=False),
                        'total': PiwikQueryReportEventMetricVisits(**self.params).get_result(reduced=False)}
        self._reduce_metrics()

    def _reduce_metrics(self):
        reduced_metrics = defaultdict(dict)

        for metric_type, records in self.metrics.iteritems():
            for date, hits in records.iteritems():
                reduced_metrics[date][metric_type] = int(hits)

        self.metrics = reduced_metrics
