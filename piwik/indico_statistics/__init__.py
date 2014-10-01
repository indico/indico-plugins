from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from MaKaC.i18n import _
from MaKaC.webinterface.wcomponents import SideMenuItem

from controllers import RHStatisticsView
from forms import SettingsForm


class StatisticsPlugin(IndicoPlugin):
    """Statistics plugin

    This statistics plugin provides statistics of conferences, meetings and
    contributions. Notice it's not designed to provide general analytics.
    """

    settings_form = SettingsForm

    def init(self):
        super(StatisticsPlugin, self).init()
        self.connect(signals.event_management_sidemenu, self.add_sidemenu_item)

    def add_sidemenu_item(self, event):
        menu_item = SideMenuItem(_("Statistics (new)"), url_for_plugin('statistics.view', event))
        return ('statistics', menu_item)

    def get_blueprints(self):
        return blueprint


blueprint = IndicoPluginBlueprint('statistics', __name__)
blueprint.add_url_rule('/event/<confId>/manage/statistics_new', 'view', RHStatisticsView)
