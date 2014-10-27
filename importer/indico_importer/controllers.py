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

from flask import jsonify
from flask_pluginengine import current_plugin

from MaKaC.webinterface.rh.base import RHProtected


class RHDataImport(RHProtected):
    """
    Fetches data from the specified importer plugin.
    Arguments:
    importer - name of an importer plugin being used
    query - string used in importer's search phrase
    size - number of returned queries
    """
    def process(self, params):
        importer = current_plugin.importers.get(params['importer_name'])
        if not importer:
            return jsonify(dict(success=False))
        query = params.get('query')
        size = params.get('size', 10)
        return importer.import_data(query, size)


class RHGetImporters(RHProtected):
    def process(self, params):
        importers = {}
        for importer in current_plugin.importers.itervalues():
            importers[importer.id] = importer.name
        return jsonify(importers)
