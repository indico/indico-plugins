# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_search.controllers import RHSearch, RHSearchCategoryTitles


blueprint = IndicoPluginBlueprint('search', 'indico_search')

blueprint.add_url_rule('/search', 'search', RHSearch)
blueprint.add_url_rule('/category/<int:category_id>/search', 'search', RHSearch)
blueprint.add_url_rule('/event/<confId>/search', 'search', RHSearch)

blueprint.add_url_rule('/category/search-titles', 'category_names', RHSearchCategoryTitles)
