from datetime import timedelta
from functools import wraps

from indico.util.date_time import format_time
from indico.util.fossilize import IFossil, fossilizes, Fossilizable
from MaKaC.common.cache import GenericCache
from MaKaC.common.timezoneUtils import nowutc, utc2server
from MaKaC.conference import ConferenceHolder

from . import PiwikPlugin
from queries.metrics import (PiwikQueryReportEventMetricReferrers, PiwikQueryReportEventMetricUniqueVisits,
                             PiwikQueryReportEventMetricVisits, PiwikQueryReportEventMetricVisitDuration,
                             PiwikQueryReportEventMetricPeakDateAndVisitors)


class IPiwikReportFossil(IFossil):
    """
    The design of this fossil, and any which inherit from it, is that there
    should be at least 3 distinct groups of what is stored for view logic and
    for caching. 'images' refers to base64 encoded image data.
    """

    def getImagesSources(self):
        pass
    getImagesSources.name = 'images'

    def getWidgetSources(self):
        pass
    getWidgetSources.name = 'widgets'

    def getValueSources(self):
        pass
    getValueSources.name = 'metrics'

    def getStartDate(self):
        pass

    def getEndDate(self):
        pass

    def getDateGenerated(self):
        pass

    def _getContributions(self):
        pass
    _getContributions.name = 'contributions'

    def getContributionId(self):
        pass
    getContributionId.name = 'contribId'

    def getConferenceId(self):
        pass
    getConferenceId.name = 'confId'


class Report(Fossilizable, object):

    fossilizes(IPiwikReportFossil)
    default_report_interval = 14

    def __init__(self, event_id, contrib_id=None, start_date=None, end_date=None):
        self.value_sources = {}
        self.contributions_info = []

        self.event = ConferenceHolder().getById(event_id)
        if self.event is None:
            raise Exception("The event does not exists")

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

        self._build_report()
        self._build_contributions_info()
        self.timestamp = utc2server(nowutc(), naive=False)

    def _build_contributions_info(self):
        """Build the list of information entries for contributions of the event"""
        contributions = self.event.getContributionList()
        if contributions:
            header = ('None', 'Event: {}'.format(self.event.getTitle()))
            self._contributions.append(header)
        for contribution in contributions:
            if not contribution.isScheduled():
                continue
            time = format_time(contribution.getStartDate())
            info = 'Contribution: {} ({})'.format(contribution.getTitle(), time)
            entry = (contribution.getUniqueId(), info)
            self.contributions_info.append(entry)

    def _build_report(self):
        """Build the report by performing queries to Piwik"""
        for query_name, query in self._queries.iteritems():
            self.value_sources[query_name] = query.get_result()

    def _init_date_range(self, start_date=None, end_date=None):
        """Set date range defaults if no dates are passed"""
        self.end_date = end_date
        self.start_date = start_date
        if self.end_date is None:
            today = nowutc().date()
            end_date = self.event.getEndDate().date()
            self.end_date = end_date if end_date < today else today
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=self.default_report_interval)


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

        # Cache bucket per implementation
        plugin = function.__module__.split('.')[3]
        self._cache = GenericCache(plugin + 'StatisticsCache')

    def getReport(self, *args, **kwargs):
        """
        Ascertain if live updating first, if so disregard and continue.
        """

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
def obtain_report(start_date, end_date, event_id, contrib_id=None):
    """Query the Piwik server and return the serialized event report"""
    if event_id is None:
        raise Exception("The event ID can't be None")
    return Report(start_date, end_date, event_id, contrib_id).fossilize()
