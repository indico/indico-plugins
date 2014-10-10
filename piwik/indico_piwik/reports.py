from datetime import timedelta

from indico.util.date_time import format_time
from indico.util.serializer import Serializer
from MaKaC.common.cache import GenericCache
from MaKaC.common.timezoneUtils import nowutc, utc2server
from MaKaC.conference import ConferenceHolder

from queries.metrics import (PiwikQueryReportEventMetricReferrers, PiwikQueryReportEventMetricUniqueVisits,
                             PiwikQueryReportEventMetricVisits, PiwikQueryReportEventMetricVisitDuration,
                             PiwikQueryReportEventMetricPeakDateAndVisitors)


class Report(Serializer):

    default_report_interval = 14

    __public__ = ['event_id', 'contrib_id', 'start_date', 'end_date', 'metrics', 'contributions', 'timestamp']

    def __init__(self, event_id, contrib_id=None, start_date=None, end_date=None):
        self.metrics = {}
        self.contributions = {}

        self.event_id = event_id
        self.contrib_id = contrib_id
        self._init_date_range(start_date, end_date)

        params = {'start_date': self.start_date,
                  'end_date': self.end_date,
                  'event_id': event_id,
                  'contrib_id': contrib_id}

        self._queries = {'visits': PiwikQueryReportEventMetricVisits(**params),
                         'uniqueVisits': PiwikQueryReportEventMetricUniqueVisits(**params),
                         'visitLength': PiwikQueryReportEventMetricVisitDuration(**params),
                         'referrers': PiwikQueryReportEventMetricReferrers(**params),
                         'peakDate': PiwikQueryReportEventMetricPeakDateAndVisitors(**params)}

        self._fetch_report()
        self._fetch_contribution_info()
        self.timestamp = utc2server(nowutc(), naive=False)

    @property
    def event(self):
        return ConferenceHolder().getById(self.event_id)

    def _fetch_contribution_info(self):
        """Build the list of information entries for contributions of the event"""
        contributions = self.event.getContributionList()
        for contribution in contributions:
            if not contribution.isScheduled():
                continue
            time = format_time(contribution.getStartDate())
            info = '{} ({})'.format(contribution.getTitle(), time)
            contrib_id = contribution.getUniqueId()
            self.contributions[contrib_id] = info

    def _fetch_report(self):
        """Build the report by performing queries to Piwik"""
        for query_name, query in self._queries.iteritems():
            self.metrics[query_name] = query.get_result()

    def _init_date_range(self, start_date=None, end_date=None):
        """Set date range defaults if no dates are passed"""
        self.end_date = end_date
        self.start_date = start_date
        if self.end_date is None:
            today = nowutc().date()
            end_date = self.event.getEndDate().date()
            self.end_date = end_date if end_date < today else today
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=Report.default_report_interval)


def obtain_report(event_id, contrib_id=None, start_date=None, end_date=None):
    """Return the serialized event report only querying the server when not in cache"""
    from . import PiwikPlugin

    if not PiwikPlugin.settings.get('cache_enabled'):
        return Report(event_id, contrib_id, start_date, end_date).to_serializable()

    cache = GenericCache('Piwik.ReportCache')
    key = '{}-{}-{}-{}'.format(event_id, contrib_id, unicode(start_date), unicode(end_date))

    report = cache.get(key)
    if not report:
        report = Report(event_id, contrib_id, start_date, end_date)
        cache.set(key, report, PiwikPlugin.settings.get('cache_ttl'))
    return report.to_serializable()
