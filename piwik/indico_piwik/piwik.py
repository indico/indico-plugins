# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import socket
from urllib2 import urlparse

import requests
from flask_pluginengine import current_plugin


class PiwikRequest(object):
    """Wrapper for Piwik API requests"""

    def __init__(self, server_url, query_script, site_id, api_token=None):
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

    @property
    def api_url(self):
        url = urlparse.urlparse(self.server_url)
        scheme = url.scheme if url.scheme else 'https'
        return '{}://{}{}{}'.format(scheme, url.netloc, url.path, self.query_script)

    def call(self, default_response=None, **query_params):
        """Perform a query to the Piwik server and return the response.

        :param default_response: Return value in case the query fails
        :param query_params: Dictionary with the parameters of the query
        """
        query_url = self.get_query_url(**query_params)
        return self._perform_call(query_url, default_response)

    def get_query(self, query_params=None):
        """Return a query string"""
        if query_params is None:
            query_params = {}
        query = ''
        query_params['idSite'] = self.site_id
        if self.api_token is not None:
            query_params['token_auth'] = self.api_token
        for key, value in query_params.iteritems():
            if isinstance(value, list):
                value = ','.join(value)
            query += '{}={}&'.format(str(key), str(value))
        return query[:-1]

    def get_query_url(self, **query_params):
        """Return the url for a Piwik API query"""
        return '{}?{}'.format(self.api_url, self.get_query(query_params))

    def _perform_call(self, query_url, default_response=None, timeout=10):
        """Returns the raw results from the API"""
        try:
            response = requests.get(query_url, timeout=timeout)
        except socket.timeout:
            current_plugin.logger.warning("Timeout contacting Piwik server")
            return default_response
        except Exception:
            current_plugin.logger.exception("Unable to connect")
            return default_response
        return response.content
