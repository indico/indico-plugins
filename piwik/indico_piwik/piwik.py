from logging import Logger
from urllib2 import urlopen, urlparse, URLError

from MaKaC.common.externalOperationsManager import ExternalOperationsManager


class PiwikRequest(object):
    """Wrapper for Piwik API requests"""

    def __init__(self, server_url, query_script, site_id, api_token=None, logger=None):
        if not server_url:
            raise ValueError("server_url can't be empty")
        if not query_script:
            raise ValueError("query_script can't be empty")
        if not site_id:
            raise ValueError("site_id can't be empty")
        self.server_url = server_url if server_url.endswith('/') else server_url + '/'
        self.query_script = query_script
        self.site_id = site_id
        self.api_token = api_token
        self.logger = logger

    @property
    def api_url(self):
        url = urlparse.urlparse(self.server_url)
        return url.netloc + url.path + self.query_script

    def call(self, default_response=None, **query_params):
        """Perform a query to the Piwik server.

        :param default_response: Return value in case the query fails
        :param query_params: Dictionary with the parameters of the query
        """
        query = self.get_query_url(**query_params)
        ExternalOperationsManager.execute(self, 'performCall', self._perform_call, query, default_response)

    def get_logger(self):
        return self.logger if self.logger else Logger()

    def get_query(self, query_params={}):
        """Return a query string"""
        query = ''
        if self.api_token is not None:
            query_params['token_auth'] = self._api_token
        for key, value in query_params.iteritems():
            if isinstance(value, list):
                value = ','.join(value)
            query += '{}={}&'.format(str(key), str(value))
        return query[:-1]

    def get_query_url(self, query_params={}):
        """Return the url for a Piwik API query"""
        return '{}?{}'.format(self.api_url, self.get_query(query_params))

    def _perform_call(self, query, default_response=None, timeout=10):
        """Returns the raw results from the API"""
        try:
            response = urlopen(url=query, timeout=timeout)
        except URLError:
            logger = self.get_logger()
            logger.exception('Unable to retrieve data')
            return default_response
        except Exception:
            logger = self.get_logger()
            logger.exception('The Piwik server did not respond')
            return default_response
        value = response.read()
        response.close()
        return value
