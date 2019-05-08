# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from base64 import b64encode

from flask_pluginengine import current_plugin

from indico_piwik.queries.base import PiwikQueryReportEventBase


class PiwikQueryReportEventGraphBase(PiwikQueryReportEventBase):
    """Base Piwik query for retrieving PNG graphs"""

    def call(self, apiModule, apiAction, height=None, width=None, graphType='verticalBar', **query_params):
        if height is not None:
            query_params['height'] = height
        if width is not None:
            query_params['width'] = width
        return super(PiwikQueryReportEventGraphBase, self).call(method='ImageGraph.get',
                                                                apiModule=apiModule, apiAction=apiAction,
                                                                aliasedGraph='1', graphType=graphType, **query_params)

    def get_result(self):
        """Perform the call and return the graph data

        :return: Encoded PNG graph data string to be inserted in a `src`
                 atribute of a HTML img tag.
        """
        png = self.call()
        if png is None:
            return
        if png.startswith('GD extension must be loaded'):
            current_plugin.logger.warning('Piwik server answered on ImageGraph.get: %s', png)
            return
        return 'data:image/png;base64,{}'.format(b64encode(png))


class PiwikQueryReportEventGraphCountries(PiwikQueryReportEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventGraphCountries, self).call(apiModule='UserCountry', apiAction='getCountry',
                                                                     period='range', width=490, height=260,
                                                                     graphType='horizontalBar', **query_params)


class PiwikQueryReportEventGraphDevices(PiwikQueryReportEventGraphBase):
    def call(self, **query_params):
        return super(PiwikQueryReportEventGraphDevices, self).call(apiModule='UserSettings', apiAction='getOS',
                                                                   period='range', width=320, height=260,
                                                                   graphType='horizontalBar', **query_params)
