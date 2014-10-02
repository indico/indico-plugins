from MaKaC.webinterface.rh.conferenceModif import RHConferenceModifBase

from .views import WPStatistics


class RHStatistics(RHConferenceModifBase):
    def _checkParams(self, params):
        RHConferenceModifBase._checkParams(self, params)
        self._params = params

    def _process(self):
        return WPStatistics.render_template('test.html', self._conf, **self._params)
