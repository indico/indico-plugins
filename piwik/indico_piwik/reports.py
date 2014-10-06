from datetime import timedelta

from indico.util.fossilize import IFossil, fossilizes, Fossilizable
from MaKaC.common.cache import GenericCache
from MaKaC.common.timezoneUtils import nowutc, utc2server
from MaKaC.conference import ConferenceHolder
from MaKaC.i18n import _

from . import PiwikPlugin
from queries.metrics import (PiwikQueryMetricConferenceVisits, PiwikQueryMetricConferenceUniqueVisits,
                             PiwikQueryMetricConferenceVisitLength, PiwikQueryMetricConferenceReferrers,
                             PiwikQueryMetricConferencePeakDateAndVisitors)


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
    _defaultReportInterval = 14

    def __init__(self, startDate, endDate, confId, contribId=None):
        # These are the containers which the report returns to the view.
        self._reportImageSources = {}
        self._reportWidgetSources = {}
        self._reportValueSources = {}

        self._reportGenerators = {}
        self._reportMethods = {}
        self._reportSetters = {}

        self._reportGenerated = None

        self._startDate = None
        self._endDate = None
        report = BaseReportGenerator

        self._reportSetters = {'images': 'setImageSource',
                               'values': 'setValueSource'}

        self._conf = ConferenceHolder().getById(confId)
        self._confId = confId
        self._contribId = contribId
        self._buildDateRange(startDate, endDate)
        self._contributions = []

        params = {'startDate': self._startDate,
                  'endDate': self._endDate,
                  'confId': confId}

        if contribId:
            params['contribId'] = contribId

        # This report only has need for images and values, not for widgets.
        self._reportGenerators = {
            'values': {'visits': report(PiwikQueryMetricConferenceVisits, params),
                       'uniqueVisits': report(PiwikQueryMetricConferenceUniqueVisits, params),
                       'visitLength': report(PiwikQueryMetricConferenceVisitLength, params),
                       'referrers': report(PiwikQueryMetricConferenceReferrers, params),
                       'peakDate': report(PiwikQueryMetricConferencePeakDateAndVisitors, params)}}

        self._buildReports()
        self._buildConferenceContributions()

    def _buildConferenceContributions(self):
        """
        As this implementation permits the viewing of individual contributions,
        we make a list of tuples associating the uniqueId with the title
        (and start time) to be fossilized.
        """
        contributions = self._conf.getContributionList()

        if contributions:
            self._contributions.append(('None', str(_('Conference: ') + self._conf.getTitle())))

            for ctrb in contributions:

                if not ctrb.isScheduled():
                    continue

                ctrbTime = str(ctrb.getStartDate().hour) + ':' + str(ctrb.getStartDate().minute)
                ctrbInfo = _('Contribution: ') + ctrb.getTitle() + ' (' + ctrbTime + ')'
                value = (ctrb.getUniqueId(), ctrbInfo)
                self._contributions.append(value)
        else:
            self._contributions = False

    def _buildDateRange(self, startDate, endDate):
        """
        If the default values are passed through, computes the appropriate date
        range based on whether today is before or after the conference end date.
        If after, end of period is set as conference end date. Start date is then
        calculated by the _defaultReportInterval difference.
        """

        def getStartDate():
            interval = timedelta(days=self._defaultReportInterval)
            adjustedStartDate = self._endDateTime - interval

            return str(adjustedStartDate.date())

        def getEndDate():
            today = nowutc()
            confEndDate = self._conf.getEndDate()

            self._endDateTime = confEndDate if today > confEndDate else today

            return str(self._endDateTime.date())

        self._endDate = endDate if endDate else getEndDate()
        self._startDate = startDate if startDate else getStartDate()

    def _buildReports(self):
        """
        All reports for this instance should be logged with a generator
        in self._reportGenerators. This method cyclces through these
        generators, executes the get command on the query object and then
        the set command on the report object.
        """

        for resultType, generators in self._reportGenerators.iteritems():
            for resultName, gen in generators.iteritems():
                setMethod = self._reportSetters.get(resultType)
                setFunc = getattr(self, setMethod)

                if setFunc is None:
                    raise Exception('Method %s not implemented' % setMethod)

                setFunc(resultName, gen.getResult())

        self._reportGenerated = utc2server(nowutc(), naive=False)

    def getDateGenerated(self):
        return self._reportGenerated

    def getImagesSources(self):
        return self._reportImageSources

    def getValueSources(self):
        return self._reportValueSources

    def getWidgetSources(self):
        return self._reportWidgetSources

    def getStartDate(self):
        return self._startDate

    def getEndDate(self):
        return self._endDate

    def _getContributions(self):
        return self._contributions

    def getConferenceId(self):
        return self._confId

    def getContributionId(self):
        return self._contribId

    def setImageSource(self, name, source):
        """
        Only want a 1:1 map of key value, each image should have its own
        title, therefore no appending to lists etc. The values of these
        associations will be the raw, base64 encoded value of the image
        itself.
        """
        sources = self.getImagesSources()
        sources[name] = source

    def setValueSource(self, name, source):
        """
        This is a map of key : value relating to metrics retrieved from
        the API which have only a string or numerical value.
        """
        sources = self.getValueSources()
        sources[name] = source

    def setWidgetSource(self, name, source):
        """
        The values of this dictionary will be the full Piwik API URLs for
        widget iframe values.
        """
        sources = self.getWidgetSources()
        sources[name] = source


class BaseReportGenerator(object):
    """
    Acts as a wrapper around a query object allowing for the Report
    object to iterate through queries to propagate with their args
    and populate its own data structures.

    @param query: Reference to uninstantiated query object
    @params arg: Dictionary of params to be passed on query instantiation.
    @param method: String name of method to be called, defaults to 'getQueryResult'
    @params funcArgs: Dictionary of args to be passed through to the called
    method, if left as None, no args passed.
    """

    def __init__(self, query, args, method='getQueryResult', funcArgs=None):
        self._query = query
        self._method = method
        self._args = args
        self._funcArgs = funcArgs

    def _performCall(self):
        """
        Instantiates the query object with the arguements provided,
        creates a reference to the required method call and returns the
        value.
        """
        queryObject = self._query(**self._args)
        func = getattr(queryObject, self._method)

        if self._funcArgs:
            return func(**self._funcArgs)
        else:
            return func()

    def getResult(self):
        """
        Wrapper around _performCall in case inheriting classes need to
        do some actions around the result before passing back.
        """
        return self._performCall()

    def getMethod(self):
        """ Returns the string method name associated with this object. """
        return self._method


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
