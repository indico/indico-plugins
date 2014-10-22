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

from __future__ import unicode_literals

from indico.core.plugins import IndicoPlugin

from indico_search.blueprint import blueprint


class SearchPlugin(IndicoPlugin):
    """Search

    Provides a base for search engine plugins.
    """

    hidden = True
    _engine_plugin = None  # the search engine plugin

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
