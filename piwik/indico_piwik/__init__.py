from urlparse import urlparse

from flask import request
from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.logger import Logger
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from MaKaC.conference import ConferenceHolder, LocalFile
from MaKaC.i18n import _
from MaKaC.webinterface.wcomponents import SideMenuItem

from .controllers import RHStatistics
from .forms import SettingsForm
from .queries import PiwikQueryTrackDownload


class PiwikPlugin(IndicoPlugin):
    """Piwik statistics plugin

    Piwik statistics plugin provides statistics of conferences, meetings
    and contributions.
    """

    settings_form = SettingsForm
    query_script = 'piwik.php'

    default_settings = {
        'enabled': True,
        'enabled_for_events': True,
        'enabled_for_downloads': True,
        'cache_enabled': True,
        'cache_ttl': 3600,
        'server_url': '//127.0.0.1/piwik/',
        'server_api_url': '//127.0.0.1/piwik/',
        'use_only_server_url': True,
        'site_id_general': 1,
        'site_id_events': 2
    }

    def init(self):
        super(PiwikPlugin, self).init()
        self.connect(signals.event_management_sidemenu, self.add_sidemenu_item)
        self.connect(signals.material_downloaded, self.track_download)
        self.template_hook('page-header', self.inject_page_header)
        self.template_hook('page-footer', self.inject_page_footer)

    def inject_page_header(self, template, **kwargs):
        server_url = self.settings.get('server_url')
        site_id_general = self.settings.get('site_id_general')
        if not self.settings.get('enabled') or not server_url or not site_id_general:
            return ''
        return render_plugin_template('site_tracking.html',
                                      site_id=site_id_general,
                                      server_url=server_url)

    def inject_page_footer(self):
        site_id_events = PiwikPlugin.settings.get('site_id_events')
        if not self.settings.get('enabled_for_events') or not site_id_events:
            return ''
        params = {'url': self._get_query_url(),
                  'site_id': site_id_events}
        if request.blueprint == 'event':
            params['event_id'] = request.view_args['confId']
            contrib_id = request.view_args.get('contribId')
            if contrib_id:
                contribution = ConferenceHolder().getById(params['event_id']).getContributionById(contrib_id)
                params['contrib_id'] = contribution.getUniqueId()
        return render_plugin_template('events_tracking.html', **params)

    def add_sidemenu_item(self, event):
        menu_item = SideMenuItem(_("Piwik Statistics"), url_for_plugin('piwik.view', event))
        return 'statistics', menu_item

    def get_blueprints(self):
        return blueprint

    def get_logger(self):
        return Logger.get('plugin.piwik')

    def register_assets(self):
        self.register_js_bundle('statistics_js', 'js/statistics.js')
        self.register_css_bundle('statistics_css', 'css/statistics.css')
        self.register_js_bundle('jqtree_js', 'js/lib/jqTree/tree.jquery.js')
        self.register_css_bundle('jqtree_css', 'js/lib/jqTree/jqtree.css')

    def track_download(self, resource):
        tracker = PiwikQueryTrackDownload()
        resource_url = request.url if isinstance(resource, LocalFile) else resource.getURL()
        resource_title = resource.getFileName() if isinstance(resource, LocalFile) else resource.getURL()
        log_title = 'Download - {}'.format(resource_title)
        tracker.trackDownload(resource_url, log_title)


blueprint = IndicoPluginBlueprint('piwik', __name__)
blueprint.add_url_rule('/event/<confId>/manage/statistics_new', 'view', RHStatistics)
