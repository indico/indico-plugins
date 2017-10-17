# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, plugin_url_rule_to_js, url_for_plugin
from indico.modules.attachments.models.attachments import AttachmentType
from indico.modules.events.contributions import Contribution
from indico.web.menu import SideMenuItem

from indico_piwik import _
from indico_piwik.controllers import (RHApiDownloads, RHApiEventGraphCountries, RHApiEventGraphDevices,
                                      RHApiEventVisitsPerDay, RHApiMaterial, RHStatistics)
from indico_piwik.forms import SettingsForm
from indico_piwik.queries.tracking import track_download_request


class PiwikPlugin(IndicoPlugin):
    """Piwik statistics

    Retrieves piwik statistics for conferences, meetings and contributions.
    """
    configurable = True
    settings_form = SettingsForm
    report_script = 'index.php'
    track_script = 'piwik.php'

    default_settings = {
        'enabled': False,
        'enabled_for_events': True,
        'enabled_for_downloads': True,
        'cache_enabled': True,
        'server_url': u'//127.0.0.1/piwik/',
        'server_api_url': u'//127.0.0.1/piwik/',
        'server_token': u'',
        'site_id_general': 1,
        'site_id_events': 2,
        'cache_ttl': 3600,
        'use_only_server_url': True,
    }

    def init(self):
        super(PiwikPlugin, self).init()
        self.connect(signals.menu.items, self.add_sidemenu_item, sender='event-management-sidemenu')
        self.connect(signals.attachments.attachment_accessed, self.track_download)
        self.template_hook('html-head', self.inject_tracking)

    def inject_tracking(self, **kwargs):
        server_url = self._get_tracking_url()
        site_id_general = self.settings.get('site_id_general')
        if not self.settings.get('enabled') or not server_url or not site_id_general:
            return ''
        event_tracking_params = self._get_event_tracking_params()
        return render_plugin_template('tracking.html',
                                      site_id_general=site_id_general,
                                      server_url=server_url,
                                      **event_tracking_params)

    def add_sidemenu_item(self, sender, event, **kwargs):
        if not event.can_manage(session.user) or not PiwikPlugin.settings.get('site_id_events'):
            return
        return SideMenuItem(u'statistics', _(u"Statistics"), url_for_plugin(u'piwik.view', event), section=u'reports')

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

    def track_download(self, attachment, from_preview, **kwargs):
        if from_preview or not self.settings.get('enabled_for_downloads'):
            return
        if attachment.type == AttachmentType.link:
            resource_url = attachment.link_url
            resource_title = u'Link - {0.title}'.format(attachment)
        else:
            resource_url = request.base_url
            resource_title = u'Download - {0.title}'.format(attachment)
        track_download_request.delay(resource_url, resource_title)

    def _get_event_tracking_params(self):
        site_id_events = PiwikPlugin.settings.get('site_id_events')
        if not self.settings.get('enabled_for_events') or not site_id_events:
            return {}
        params = {'site_id_events': site_id_events}
        if request.blueprint in ('event', 'events', 'contributions') and 'confId' in request.view_args:
            params['event_id'] = request.view_args['confId']
            contrib_id = request.view_args.get('contrib_id')
            if contrib_id is not None:
                contribution = Contribution.find_first(event_id=params['event_id'], id=contrib_id)
                if contribution:
                    cid = (contribution.legacy_mapping.legacy_contribution_id if contribution.legacy_mapping
                           else contribution.id)
                    params['contrib_id'] = '{}t{}'.format(contribution.event_id, cid)
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
