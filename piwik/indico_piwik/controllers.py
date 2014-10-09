from indico.core.config import Config
from indico.util.i18n import _
from MaKaC.webinterface.rh.conferenceModif import RHConferenceModifBase

from .views import WPStatistics
from .reports import obtain_report


class RHStatistics(RHConferenceModifBase):
    def _checkParams(self, params):
        RHConferenceModifBase._checkParams(self, params)
        self._params = params
        self._params['loading_gif'] = '{}/images/loading.gif'.format(Config.getInstance().getBaseURL())
        self._params['str_modif_query'] = _('Modify Query')
        self._params['str_hide_query'] = _('Hide Modify Query')
        self._params['str_no_graph'] = _('No graph data was returned by the server, please alter the date range.')
        self._params['report'] = obtain_report(event_id=params.get('confId'), contrib_id=params.get('contribId'),
                                               start_date=params.get('startDate'), end_date=params.get('endDate'))

    def _process(self):
        return WPStatistics.render_template('statistics.html', self._conf, **self._params)
