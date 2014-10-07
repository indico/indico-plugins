from functools import wraps
from urllib2 import urlopen, urlparse, URLError

from MaKaC.common.externalOperationsManager import ExternalOperationsManager

from . import PiwikPlugin
from .report import CachedReport


def memoizeReport(function):
    """
    Decorator method for the get<reports> methods, see CachedReport for
    details on how this works with GenericCache.
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        return CachedReport(function).getReport(*args, **kwargs)

    return wrapper


class Piwik(object):
    """Wrapper for Piwik RESTful API for constructing and executing calls"""

    QUERY_JOIN = '&'
    QUERY_BREAK = ';'
    QUERY_SCRIPT = 'piwik.php'
    QUERY_KEY_NAME = 'token_auth'

    def __init__(self):
        self._api_params = {}
        self._api_required_params = []
        self._api_token = PiwikPlugin.settings.get('server_token')
        self._APIPath = None
        self._APIQuery = None
        self._APISegmentation = []

    @property
    def site_id(self):
        return PiwikPlugin.settings.get('site_id')

    @staticmethod
    @memoizeReport
    def getConferenceReport(startDate, endDate, confId, contribId=None):
        """
        Returns the report object which satisifies the confId given.
        """
        from indico.ext.statistics.piwik.reports import PiwikReport
        return PiwikReport(startDate, endDate, confId, contribId).fossilize()

    @staticmethod
    def getContributionReport(startDate, endDate, confId, contribId):
        """
        Returns the report object for the contribId given.
        """
        return Piwik.getConferenceReport(startDate, endDate, confId, contribId)

    def _buildAPIQuery(self, params=None):
        """Build an API query

        :param params: Dictionary of parameters to be added to the query
        """

        if params is not None:
            self.setAPIParams(params)

        query = ""
        params = self._api_params

        if self._api_token is not None:
            params[self.QUERY_KEY_NAME] = self._api_token

        for key in params:
            value = ""

            if isinstance(self._api_params.get(key), list):
                value = self._api_params.get(key).join(',')
            else:
                value = self._api_params.get(key)

            query += str(key) + "=" + str(value) + self.QUERY_JOIN

        self._APIQuery = query[:-1]

    def _getMissingRequiredAPIParams(self):
        """
        Returns a list of order U\A difference between the required params
        and those provided.
        """
        required = set(self._api_required_params)
        given = set(self._api_params)

        return list(required.difference(given))

    def _hasAllRequiredParams(self):
        """
        Some API implementations require certain parameters, ascertains
        if all are satisfied.
        """

        if len(self._api_required_params) == 0:
            return True

        for param in self._api_required_params:
            if param not in self._api_params:
                return False

        return True

    def _get_api_path(self, use_primary_server=True):
        if PiwikPlugin.settings.get('use_only_server_url') or use_primary_server:
            path = PiwikPlugin.settings.get('server_url')
        else:
            path = PiwikPlugin.settings.get('server_api_url')
        if path is None:
            return
        if not path.endswith('/'):
            path += '/'
        url = urlparse(path)
        return url.netloc + url.path

    def getAPIPath(self, http=False, https=False, with_script=False):
        """
        Returns the API path, which is considered to be the locatable
        address of the server hosting the tracking software. May
        designate HTTP or HTTPS prefix, or neither.
        If both defined, HTTPS takes priority.
        """
        path = self._get_api_path()

        if with_script:
            path += self.QUERY_SCRIPT + "?"

        if https:
            return 'https://' + path
        elif http:
            return 'http://' + path
        else:
            return path

    def clearAPIParams(self):
        """
        Clears the internal params buffer.
        """
        self._api_params = {}

    def setAPIParams(self, params):
        """
        Internal mechanism for storing parameters for the query using
        a dictionary (params) of key=value.
        """
        for key, value in params.iteritems():

            if value is None:
                del self._api_params[key]
            else:
                self._api_params[key] = value

    def setAPIAction(self, action):
        self.setAPIParams({'action': action})

    def setAPIInnerAction(self, action):
        self.setAPIParams({'apiAction': action})

    def setAPIMethod(self, method):
        self.setAPIParams({'method': method})

    def setAPIModule(self, module):
        self.setAPIParams({'module': module})

    def setAPIInnerModule(self, module):
        self.setAPIParams({'apiModule': module})

    def setAPIFormat(self, format='JSON'):
        self.setAPIParams({'format': format})

    def setAPIPeriod(self, period='day'):
        self.setAPIParams({'period': period})

    def setAPIDate(self, date=['last7']):
        newDate = date[0] if len(date) == 1 else ','.join(date)
        self.setAPIParams({'date': newDate})

    def setAPISegmentation(self, segmentation):
        """
        segmentation = {'key': ('equality', 'value')}
        """

        for segmentName, (equality, segmentValue) in segmentation.iteritems():
            if isinstance(segmentValue, list):
                value = ','.join(segmentValue)
            else:
                value = str(segmentValue)

            segmentBuild = segmentName + equality + value

            if segmentBuild not in self._APISegmentation:
                self._APISegmentation.append(segmentBuild)

        segmentation = self.QUERY_BREAK.join(self._APISegmentation)

        self.setAPIParams({'segment': segmentation})

    def getLogger(self):
        """
        Returns the logger for this implementation.
        """
        return PiwikPlugin.get_logger()

    def getAPIQuery(self, onlyQuery=False, http=False, https=False, withScript=False):
        """
        Triggers internal build of query and returns the full path by
        default, can return only the query string if flag onlyQuery is true.
        """

        if not self._hasAllRequiredParams():
            exc = 'Cannot call API without all required parameters, missing: '
            exc += str(self._getMissingRequiredAPIParams())
            raise Exception(exc)

        self._buildAPIQuery()

        if onlyQuery:
            return self._APIQuery

        return self.getAPIPath(http, https, withScript) + self._APIQuery

    def _performCall(self, default=None):
        """
        Acts as an entry point for all derivative classes to use the
        ExternalOperationsManager for performing remote calls.
        """
        return ExternalOperationsManager.execute(self,
                                                 "performCall",
                                                 self._performExternalCall,
                                                 default)

    def _performExternalCall(self, default=None):
        """
        Returns the raw results from the API to be handled elsewhere before
        being passed through to the report.
        """
        timeout = 10  # Timeout in seconds to end the call

        try:
            response = urlopen(url=self.getAPIQuery(), timeout=timeout)
        except URLError, e:
            # In case of timeout, log the incident and return the default value.
            logger = self.getLogger()
            logger.exception('Unable to retrieve data, exception: %s' % str(e))
            return default
        except:
            # For other exceptions, log the incident and return the default value.
            logger = self.getLogger()
            logger.exception('The Piwik server did not respond')
            return default

        value = response.read()
        response.close()
        return value
