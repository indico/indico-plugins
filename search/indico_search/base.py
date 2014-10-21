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

from flask_pluginengine import depends

from indico.core.plugins import IndicoPlugin

from indico_search.plugin import SearchPlugin


@depends('search')
class SearchPluginBase(IndicoPlugin):
    """Base class for search engine plugins"""

    def init(self):
        super(SearchPluginBase, self).init()
        SearchPlugin.instance.engine = self
