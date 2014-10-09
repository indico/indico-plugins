from datetime import timedelta
from functools import wraps

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

        self.event = ConferenceHolder().getById(event_id)
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


class CachedReport(object):
    """
    This class acts as a wrapper for functions which return a report object,
    by decorating the get<report> methods with the memonize function in the
    BaseStatisticsReport object, the result is wrapped here and its age
    is compared with the TTL if in the cache, either returning said item or
    allowing the method to generate a new one.
    """

    def __init__(self, function):
        self._function = function
        self._cache = GenericCache('Piwik.ReportCache')

    def getReport(self, *args, **kwargs):
        """
        Ascertain if live updating first, if so disregard and continue.
        """
        from . import PiwikPlugin

        if not PiwikPlugin.settings.get('cache_enabled'):
            return self._function(*args, **kwargs)

        keyParams = list(args)
        keyParams.extend([self._function.__module__, self._function.__name__])
        key = self._generateKey(keyParams)

        resource = self._cache.get(key, None)

        if not resource:
            result = self._function(*args, **kwargs)
            ttl = PiwikPlugin.settings.get('cache_ttl')
            self._cache.set(key, result, ttl)
            return result
        else:
            return resource

    def _generateKey(self, params):
        """
        Generates a unique key for caching against the params given.
        """
        return reduce(lambda x, y: str(x) + '-' + str(y), params)


def memoize_report(function):
    """
    Decorator method for the get<reports> methods, see CachedReport for
    details on how this works with GenericCache.
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        return CachedReport(function).getReport(*args, **kwargs)

    return wrapper


@memoize_report
def obtain_report(event_id, contrib_id=None, start_date=None, end_date=None):
    """Query the Piwik server and return the serialized event report"""
    if event_id is None:
        raise Exception("The event ID can't be None")
    return Report(event_id, contrib_id, start_date, end_date).to_serializable()
