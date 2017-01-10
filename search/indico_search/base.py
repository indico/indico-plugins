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

from flask import session
from flask_pluginengine import depends

from indico.core.plugins import IndicoPlugin, PluginCategory

from indico_search.forms import SearchForm
from indico_search.plugin import SearchPlugin


@depends('search')
class SearchPluginBase(IndicoPlugin):
    """Base class for search engine plugins"""

    #: the SearchEngine subclass to use
    engine_class = None
    #: the SearchForm subclass to use
    search_form = SearchForm
    category = PluginCategory.search

    def init(self):
        super(SearchPluginBase, self).init()
        SearchPlugin.instance.engine_plugin = self

    @property
    def only_public(self):
        """If the search engine only returns public events"""
        return session.user is None

    def perform_search(self, values, obj=None, obj_type=None):
        """Performs the search.

        For documentation on the parameters and return value, see
        the documentation of the :class:`SearchEngine` class.
        """
        return self.engine_class(values, obj, obj_type).process()


class SearchEngine(object):
    """Base class for a search engine"""

    def __init__(self, values, obj, obj_type):
        """
        :param values: the values sent by the user
        :param obj: object to search in (a `Category` or `Conference`)
        """
        self.values = values
        self.obj = obj
        self.obj_type = obj_type
        self.user = session.user

    def process(self):
        """Executes the search

        :return: an object that's passed directly to the result template.
                 if a flask response is returned, it is sent to the client
                 instead (useful to redirect to an external page)
        """
        raise NotImplementedError
