from urllib2 import urlparse

from flask import request
from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.logger import Logger
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from indico.util.i18n import _
from MaKaC.conference import ConferenceHolder, LocalFile
from MaKaC.webinterface.wcomponents import SideMenuItem

from .controllers import (RHStatistics, RHApiMaterial, RHApiDownloads, RHApiEventVisits,
                          RHApiEventGraphCountries, RHApiEventGraphDevices)
from .forms import SettingsForm
from .queries.tracking import PiwikQueryTrackDownload


class PiwikPlugin(IndicoPlugin):
    """Piwik statistics plugin

    Piwik statistics plugin provides statistics of conferences, meetings
    and contributions.
    """

    settings_form = SettingsForm
    report_script = 'index.php'
    track_script = 'piwik.php'

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

    @staticmethod
    def get_logger():
        return Logger.get('plugin.piwik')

    def init(self):
        super(PiwikPlugin, self).init()
        self.connect(signals.event_management_sidemenu, self.add_sidemenu_item)
        self.connect(signals.material_downloaded, self.track_download)
        self.template_hook('page-header', self.inject_tracking)

    def inject_tracking(self, template, **kwargs):
        server_url = self._get_tracking_url()
        site_id_general = self.settings.get('site_id_general')
        if not self.settings.get('enabled') or not server_url or not site_id_general:
            return ''
        event_tracking_params = self._get_event_tracking_params()
        return render_plugin_template('tracking.html',
                                      site_id_general=site_id_general,
                                      server_url=server_url,
                                      **event_tracking_params)

    def add_sidemenu_item(self, event):
        menu_item = SideMenuItem(_("Piwik Statistics"), url_for_plugin('piwik.view', event))
        return 'statistics', menu_item

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_js_bundle('statistics_js', 'js/statistics.js')
        self.register_css_bundle('statistics_css', 'css/statistics.css')
        self.register_js_bundle('jqtree_js', 'js/lib/jqTree/tree.jquery.js')
        self.register_css_bundle('jqtree_css', 'js/lib/jqTree/jqtree.css')

    def track_download(self, event, resource):
        tracker = PiwikQueryTrackDownload()
        resource_url = request.url if isinstance(resource, LocalFile) else resource.getURL()
        resource_title = resource.getFileName() if isinstance(resource, LocalFile) else resource.getURL()
        resource_title = 'Download - {}'.format(resource_title)
        tracker.call(resource_url, resource_title)

    def _get_event_tracking_params(self):
        site_id_events = PiwikPlugin.settings.get('site_id_events')
        if not self.settings.get('enabled_for_events') or not site_id_events:
            return {}
        params = {'site_id_events': site_id_events}
        if request.blueprint == 'event':
            params['event_id'] = request.view_args['confId']
            contrib_id = request.view_args.get('contribId')
            if contrib_id:
                contribution = ConferenceHolder().getById(params['event_id']).getContributionById(contrib_id)
                params['contrib_id'] = contribution.getUniqueId()
        return params

    def _get_tracking_url(self):
        url = self.settings.get('server_url')
        url = url if url.endswith('/') else url + '/'
        url = urlparse.urlparse(url)
        return url.netloc + url.path


blueprint = IndicoPluginBlueprint('piwik', __name__)
blueprint.add_url_rule('/event/<confId>/manage/statistics', 'view', RHStatistics)
blueprint.add_url_rule('/event/<confId>/manage/statistics/material', 'material', RHApiMaterial)
blueprint.add_url_rule('/event/<confId>/manage/statistics/data/downloads', 'data-downloads', RHApiDownloads)
blueprint.add_url_rule('/event/<confId>/manage/statistics/data/visits', 'data-visits', RHApiEventVisits)
blueprint.add_url_rule('/event/<confId>/manage/statistics/graph/countries', 'graph-countries', RHApiEventGraphCountries)
blueprint.add_url_rule('/event/<confId>/manage/statistics/graph/devices', 'graph-devices', RHApiEventGraphDevices)
