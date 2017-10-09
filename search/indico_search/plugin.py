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

from __future__ import unicode_literals

from flask import g, request
from flask_pluginengine import plugins_loaded

from indico.core.plugins import IndicoPlugin, PluginCategory
from indico.modules.events.layout import layout_settings

from indico_search.blueprint import blueprint
from indico_search.util import render_engine_or_search_template


class SearchPlugin(IndicoPlugin):
    """Search

    Provides a base for search engine plugins.
    """
    category = PluginCategory.search
    _engine_plugin = None  # the search engine plugin

    def init(self):
        super(SearchPlugin, self).init()
        self.connect(plugins_loaded, self._plugins_loaded, sender=self.app)
        self.template_hook('conference-header-right-column', self._add_conference_search_box)
        self.template_hook('page-header', self._add_category_search_box)
        self.inject_js('search_js')
        self.inject_css('search_css')

    def register_assets(self):
        self.register_js_bundle('search_js', 'js/search.js')
        self.register_css_bundle('search_css', 'css/search.scss')

    def _plugins_loaded(self, sender, **kwargs):
        if not self.engine_plugin:
            raise RuntimeError('Search plugin active but no search engine plugin loaded')

    @property
    def engine_plugin(self):
        return self._engine_plugin

    @engine_plugin.setter
    def engine_plugin(self, value):
        if self._engine_plugin is not None:
            raise RuntimeError('Another search engine plugin is active: {}'.format(self._engine_plugin.name))
        self._engine_plugin = value

    def get_blueprints(self):
        return blueprint

    def _add_conference_search_box(self, event, **kwargs):
        if layout_settings.get(event, 'is_searchable') and not g.get('static_site'):
            form = self.engine_plugin.search_form(prefix='search-', csrf_enabled=False)
            return render_engine_or_search_template('searchbox_conference.html', event=event, form=form)

    def _add_category_search_box(self, category, **kwargs):
        if request.blueprint != 'plugin_search':
            form = self.engine_plugin.search_form(prefix='search-', csrf_enabled=False)
            return render_engine_or_search_template('searchbox_category.html', category=category, form=form)
