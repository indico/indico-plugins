# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import os

from flask import g, request
from flask_pluginengine import plugins_loaded

from indico.core.plugins import IndicoPlugin, PluginCategory
from indico.modules.events.layout import layout_settings
from indico.web.views import WPBase

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
        self.inject_bundle('main.js', WPBase)
        self.inject_bundle('main.css', WPBase)

    def _plugins_loaded(self, sender, **kwargs):
        if not self.engine_plugin and 'INDICO_DUMPING_URLS' not in os.environ:
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
