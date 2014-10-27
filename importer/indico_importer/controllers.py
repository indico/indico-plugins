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
