# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from urllib2 import urlparse

from flask import request, session
from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin, plugin_url_rule_to_js
from indico.util.i18n import _
from MaKaC.accessControl import AccessWrapper
from MaKaC.conference import ConferenceHolder, LocalFile
from MaKaC.webinterface.wcomponents import SideMenuItem

from indico_piwik.controllers import (RHStatistics, RHApiMaterial, RHApiDownloads, RHApiEventVisitsPerDay,
                                      RHApiEventGraphCountries, RHApiEventGraphDevices)
from indico_piwik.forms import SettingsForm
from indico_piwik.queries.tracking import PiwikQueryTrackDownload


class PiwikPlugin(IndicoPlugin):
    """Piwik statistics

    Retrieves piwik statistics for conferences, meetings and contributions.
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

    def init(self):
        super(PiwikPlugin, self).init()
        self.connect(signals.event_management.sidemenu, self.add_sidemenu_item)
        self.connect(signals.event.material_downloaded, self.track_download)
        self.template_hook('html-head', self.inject_tracking)

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

    def add_sidemenu_item(self, event, **kwargs):
        if event.canModify(AccessWrapper(session.user)):
            menu_item = SideMenuItem(_("Statistics"), url_for_plugin('piwik.view', event))
            return 'statistics', menu_item

    def get_blueprints(self):
        return blueprint

    def get_vars_js(self):
        return {'urls': {'material': plugin_url_rule_to_js('piwik.material'),
                         'data_downloads': plugin_url_rule_to_js('piwik.data_downloads'),
                         'data_visits': plugin_url_rule_to_js('piwik.data_visits'),
                         'graph_countries': plugin_url_rule_to_js('piwik.graph_countries'),
                         'graph_devices': plugin_url_rule_to_js('piwik.graph_devices')}}

    def register_assets(self):
        self.register_js_bundle('statistics_js', 'js/statistics.js')
        self.register_css_bundle('statistics_css', 'css/statistics.css')
        self.register_js_bundle('jqtree_js', 'js/lib/jqTree/tree.jquery.js')
        self.register_css_bundle('jqtree_css', 'js/lib/jqTree/jqtree.css')

    def track_download(self, event, resource, **kwargs):
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


blueprint = IndicoPluginBlueprint('piwik', __name__, url_prefix='/event/<confId>/manage/statistics')
blueprint.add_url_rule('/', 'view', RHStatistics)
blueprint.add_url_rule('/material', 'material', RHApiMaterial, methods=('GET', 'POST'))
blueprint.add_url_rule('/data/downloads', 'data_downloads', RHApiDownloads, methods=('GET', 'POST'))
blueprint.add_url_rule('/data/visits', 'data_visits', RHApiEventVisitsPerDay, methods=('GET', 'POST'))
blueprint.add_url_rule('/graph/countries', 'graph_countries', RHApiEventGraphCountries, methods=('GET', 'POST'))
blueprint.add_url_rule('/graph/devices', 'graph_devices', RHApiEventGraphDevices, methods=('GET', 'POST'))
