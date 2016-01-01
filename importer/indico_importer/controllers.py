# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

from flask import jsonify, request
from flask_pluginengine import current_plugin

from MaKaC.webinterface.rh.base import RHProtected


class RHGetImporters(RHProtected):
    def _process(self):
        importers = {k: importer.name for k, (importer, _) in current_plugin.importer_engines.iteritems()}
        return jsonify(importers)


class RHImportData(RHProtected):
    def _process(self):
        size = request.args.get('size', 10)
        query = request.args.get('query')
        importer, plugin = current_plugin.importer_engines.get(request.view_args['importer_name'])
        with plugin.plugin_context():
            data = {'records': importer.import_data(query, size)}
        return jsonify(data)
