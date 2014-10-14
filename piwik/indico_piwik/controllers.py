from flask import jsonify

from indico.core.config import Config
from indico.util.i18n import _
from MaKaC.conference import ConferenceHolder
from MaKaC.webinterface.rh.conferenceModif import RHConferenceModifBase

from .views import WPStatistics
from .reports import ReportCountries, ReportDevices, ReportDownloads, ReportGeneral, ReportVisitsPerDay


class RHStatistics(RHConferenceModifBase):
    def _checkParams(self, params):
        RHConferenceModifBase._checkParams(self, params)
        self._params = params
        self._params['loading_gif'] = '{}/images/loading.gif'.format(Config.getInstance().getBaseURL())
        self._params['str_modif_query'] = _('Modify Query')
        self._params['str_hide_query'] = _('Hide Modify Query')
        self._params['str_no_graph'] = _('No graph data was returned by the server, please alter the date range.')
        self._params['report'] = ReportGeneral.get(event_id=params.get('confId'), contrib_id=params.get('contribId'),
                                                   start_date=params.get('startDate'), end_date=params.get('endDate'))

    def _process(self):
        return WPStatistics.render_template('statistics.html', self._conf, **self._params)


class RHApiBase(RHConferenceModifBase):
    def _checkParams(self, params):
        RHConferenceModifBase._checkParams(self, params)
        self._report_params = {'start_date': params.get('startDate'),
                               'end_date': params.get('endDate')}


class RHApiEventBase(RHApiBase):
    def _checkParams(self, params):
        RHApiBase._checkParams(self, params)
        self._report_params['event_id'] = params['confId']
        self._report_params['contrib_id'] = params.get('contrib_id')


class RHApiDownloads(RHApiBase):
    def _checkParams(self, params):
        RHApiBase._checkParams(self, params)
        self._report_params['download_url'] = params['download_url']

    def _process(self):
        return jsonify(ReportDownloads.get(**self._report_params))


class RHApiEventVisitsPerDay(RHApiEventBase):
    def _process(self):
        return jsonify(ReportVisitsPerDay.get(**self._report_params))


class RHApiEventGraphCountries(RHApiEventBase):
    def _process(self):
        return jsonify(ReportCountries.get(**self._report_params))


class RHApiEventGraphDevices(RHApiEventBase):
    def _process(self):
        return jsonify(ReportDevices.get(**self._report_params))


class RHApiMaterial(RHApiBase):
    """
    HTTP method for getting the Material dictionary of a Conference in
    the format jqTree expects.
    """

    TREE_STR_LIMIT = 24

    # @BaseStatisticsImplementation.memoizeReport
    def _process(self):
        confId = self._conf.getId()
        conference = ConferenceHolder().getById(confId)
        material = conference.getAllMaterialDict()

        return self.formatForJQTree(material, returnAsList=True)

    def formatForJQTree(self, child, returnAsList=False):
        """
        Wraps around the JSON output in Conference to the specific
        format required by jqTree.
        """

        node = {}
        node['label'] = child['title']
        node['children'] = []

        for key, value in child.iteritems():

            if key not in ['children', 'material']:  # Performance only
                continue

            children = []

            if key == 'children' and len(value) > 0:

                for child in value:
                    newNode = self.formatForJQTree(child)

                    if newNode:
                        children.append(newNode)

            if key == 'material' and len(value) > 0:

                for material in value:
                    newNode = {}
                    newNode['label'] = material['title']
                    newNode['id'] = material['url']

                    children.append(newNode)

            if children:
                node['children'].extend(children)

        # If the node has no children (i.e. Sessions, Contributions & Material,
        # then there is no point in displaying it in the tree.
        if len(node['children']) > 0:

            self.shortenNodeLabel(node)

            for child in node['children']:
                self.shortenNodeLabel(child)

            return [node] if returnAsList else node
        else:
            return None

    def shortenNodeLabel(self, node):
        """
        We don't want the strings to be massive in the labels, truncate them
        to make the tree more manageable.
        """
        if len(node['label']) > self.TREE_STR_LIMIT:
            node['label'] = node['label'][:self.TREE_STR_LIMIT] + '...'
