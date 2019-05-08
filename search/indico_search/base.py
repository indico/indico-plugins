# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
