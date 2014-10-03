from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from MaKaC.i18n import _
from MaKaC.webinterface.wcomponents import SideMenuItem

from .controllers import RHStatistics
from .forms import SettingsForm


class PiwikPlugin(IndicoPlugin):
    """Piwik statistics plugin

    Piwik statistics plugin provides statistics of conferences, meetings
    and contributions.
    """

    settings_form = SettingsForm

    def init(self):
        super(PiwikPlugin, self).init()
        self.connect(signals.event_management_sidemenu, self.add_sidemenu_item)
        self.template_hook('page-header', self.inject_page_header)

    def add_sidemenu_item(self, event):
        menu_item = SideMenuItem(_("Piwik Statistics"), url_for_plugin('piwik.view', event))
        return ('statistics', menu_item)

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_js_bundle('statistics_js', 'js/statistics.js')
        self.register_css_bundle('statistics_css', 'css/statistics.css')
        self.register_js_bundle('jqtree_js', 'js/lib/jqTree/tree.jquery.js')
        self.register_css_bundle('jqtree_css', 'js/lib/jqTree/jqtree.css')

    def inject_page_header(self, template, **kwargs):
        server_url = self.settings.get('server_url')

        if not self.settings.get('enabled') or not server_url:
            return ""
        else:
            return render_plugin_template('site_tracking.html',
                                          site_id=self.settings.get('site_id_general'),
                                          server_url=server_url)


blueprint = IndicoPluginBlueprint('piwik', __name__)
blueprint.add_url_rule('/event/<confId>/manage/statistics_new', 'view', RHStatistics)
