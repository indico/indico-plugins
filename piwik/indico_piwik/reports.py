from collections import defaultdict
from datetime import timedelta

from indico.util.date_time import format_time
from indico.util.serializer import Serializer
from MaKaC.common.cache import GenericCache
from MaKaC.common.timezoneUtils import nowutc, utc2server
from MaKaC.conference import ConferenceHolder

from .queries.graphs import PiwikQueryReportEventGraphCountries, PiwikQueryReportEventGraphDevices
from .queries.metrics import (PiwikQueryReportEventMetricDownloads, PiwikQueryReportEventMetricPeakDateAndVisitors,
                              PiwikQueryReportEventMetricReferrers, PiwikQueryReportEventMetricUniqueVisits,
                              PiwikQueryReportEventMetricVisits, PiwikQueryReportEventMetricVisitDuration)


class ReportBase(Serializer):
    """Wrapper for Piwik report collection"""

    __public__ = []
    default_report_interval = 14

    def __init__(self, event_id, contrib_id=None, start_date=None, end_date=None, **report_params):
        self.graphs = {}
        self.metrics = {}
        self.event_id = event_id
        self.contrib_id = contrib_id
        self._init_date_range(start_date, end_date)
        self.params = {'start_date': self.start_date,
                       'end_date': self.end_date,
                       'event_id': self.event_id,
                       'contrib_id': self.contrib_id}
        self._build_report(**report_params)
        self.timestamp = utc2server(nowutc(), naive=False)

    def _build_report(self):
        """To be overriden"""
        pass

    def _init_date_range(self, start_date=None, end_date=None):
        """Set date range defaults if no dates are passed"""
        self.end_date = end_date
        self.start_date = start_date
        if self.end_date is None:
            today = nowutc().date()
            end_date = self.event.getEndDate().date()
            self.end_date = end_date if end_date < today else today
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=ReportBase.default_report_interval)


class ReportCountries(ReportBase):
    __public__ = ['graphs']

    def _build_report(self):
        self.graphs['countries'] = PiwikQueryReportEventGraphCountries(**self.params).get_result()


class ReportDevices(ReportBase):
    __public__ = ['graphs']

    def _build_report(self):
        self.graphs['devices'] = PiwikQueryReportEventGraphDevices(**self.params).get_result()


class ReportDownloads(ReportBase):
    __public__ = ['metrics']

    def _build_report(self, download_url):
        self.metrics['downloads'] = PiwikQueryReportEventMetricDownloads(**self.params).get_result(download_url)


class ReportGeneral(ReportBase):
    __public__ = ['event_id', 'contrib_id', 'start_date', 'end_date', 'metrics', 'contributions', 'timestamp']

    @property
    def event(self):
        return ConferenceHolder().getById(self.event_id)

    def _build_report(self):
        """Build the report by performing queries to Piwik"""
        queries = {'visits': PiwikQueryReportEventMetricVisits(**self.params),
                   'uniqueVisits': PiwikQueryReportEventMetricUniqueVisits(**self.params),
                   'visitLength': PiwikQueryReportEventMetricVisitDuration(**self.params),
                   'referrers': PiwikQueryReportEventMetricReferrers(**self.params),
                   'peakDate': PiwikQueryReportEventMetricPeakDateAndVisitors(**self.params)}

        for query_name, query in queries.iteritems():
            self.metrics[query_name] = query.get_result()

        self._fetch_contribution_info()

    def _fetch_contribution_info(self):
        """Build the list of information entries for contributions of the event"""
        self.contributions = {}

        contributions = self.event.getContributionList()
        for contribution in contributions:
            if not contribution.isScheduled():
                continue
            time = format_time(contribution.getStartDate())
            info = '{} ({})'.format(contribution.getTitle(), time)
            contrib_id = contribution.getUniqueId()
            self.contributions[contrib_id] = info


class ReportVisits(ReportBase):
    __public__ = ['metrics']

    def _build_report(self):
        self.metrics['unique'] = PiwikQueryReportEventMetricUniqueVisits(**self.params).get_result()
        self.metrics['total'] = PiwikQueryReportEventMetricVisits(**self.params).get_result()
        self._reduce_metrics()

    def _reduce_metrics(self):
        reduced_metrics = defaultdict(dict)

        for metric_type, records in self.metrics.iteritems():
            for date, hits in records.iteritems():
                reduced_metrics[date][metric_type] = int(hits)

        self.metrics = reduced_metrics


def obtain_report(event_id, contrib_id=None, start_date=None, end_date=None):
    """Return the serialized event report only querying the server when not in cache"""
    from . import PiwikPlugin

    if not PiwikPlugin.settings.get('cache_enabled'):
        return ReportGeneral(event_id, contrib_id, start_date, end_date).to_serializable()

    cache = GenericCache('Piwik.ReportCache')
    key = '{}-{}-{}-{}'.format(event_id, contrib_id, unicode(start_date), unicode(end_date))

    report = cache.get(key)
    if not report:
        report = ReportGeneral(event_id, contrib_id, start_date, end_date)
        cache.set(key, report, PiwikPlugin.settings.get('cache_ttl'))
    return report.to_serializable()
