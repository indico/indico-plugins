from indico.core.plugins import WPJinjaMixinPlugin
from MaKaC.webinterface.pages.conferences import WPConferenceModifBase


class WPStatistics(WPJinjaMixinPlugin, WPConferenceModifBase):
    def _setActiveSideMenuItem(self):
        self._pluginMenuItems['statistics'].setActive()
