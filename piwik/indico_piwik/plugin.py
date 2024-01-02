# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from urllib.parse import urlparse

from flask import request, session
from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, plugin_url_rule_to_js, url_for_plugin
from indico.modules.events.contributions import Contribution
from indico.web.menu import SideMenuItem

from indico_piwik import _
from indico_piwik.controllers import (RHApiEventGraphCountries, RHApiEventGraphDevices, RHApiEventVisitsPerDay,
                                      RHStatistics)
from indico_piwik.forms import SettingsForm


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
        'cache_enabled': True,
        'server_url': '//127.0.0.1/piwik/',
        'server_api_url': '//127.0.0.1/piwik/',
        'server_token': '',
        'site_id_general': 1,
        'site_id_events': 2,
        'cache_ttl': 3600,
        'use_only_server_url': True,
    }

    def init(self):
        super().init()
        self.connect(signals.menu.items, self.add_sidemenu_item, sender='event-management-sidemenu')
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
        return SideMenuItem('statistics', _('Statistics'), url_for_plugin('piwik.view', event), section='reports')

    def get_blueprints(self):
        return blueprint

    def get_vars_js(self):
        return {'urls': {'data_visits': plugin_url_rule_to_js('piwik.data_visits'),
                         'graph_countries': plugin_url_rule_to_js('piwik.graph_countries'),
                         'graph_devices': plugin_url_rule_to_js('piwik.graph_devices')}}

    def _get_event_tracking_params(self):
        site_id_events = PiwikPlugin.settings.get('site_id_events')
        if not self.settings.get('enabled_for_events') or not site_id_events:
            return {}
        params = {'site_id_events': site_id_events}
        if request.blueprint in ('event', 'events', 'contributions') and 'event_id' in request.view_args:
            params['event_id'] = request.view_args['event_id']
            contrib_id = request.view_args.get('contrib_id')
            if contrib_id is not None and str(contrib_id).isdigit():
                contribution = Contribution.query.filter_by(event_id=params['event_id'], id=contrib_id).first()
                if contribution:
                    cid = (contribution.legacy_mapping.legacy_contribution_id if contribution.legacy_mapping
                           else contribution.id)
                    params['contrib_id'] = f'{contribution.event_id}t{cid}'
        return params

    def _get_tracking_url(self):
        url = self.settings.get('server_url')
        url = url if url.endswith('/') else url + '/'
        url = urlparse(url)
        return url.netloc + url.path


blueprint = IndicoPluginBlueprint('piwik', __name__, url_prefix='/event/<int:event_id>/manage/statistics')
blueprint.add_url_rule('/', 'view', RHStatistics)
blueprint.add_url_rule('/data/visits', 'data_visits', RHApiEventVisitsPerDay, methods=('GET', 'POST'))
blueprint.add_url_rule('/graph/countries', 'graph_countries', RHApiEventGraphCountries, methods=('GET', 'POST'))
blueprint.add_url_rule('/graph/devices', 'graph_devices', RHApiEventGraphDevices, methods=('GET', 'POST'))
