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

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, plugin_url_rule_to_js
from MaKaC.webinterface.pages.conferences import WPConfModifScheduleGraphic
from indico.util.i18n import _

from .controllers import RHGetImporters, RHImportData


class ImporterPlugin(IndicoPlugin):
    """Importer

    Extends Indico for other plugins to import data from external sources to
    the timetable.
    """

    hidden = True
    category = 'import'

    def init(self):
        super(ImporterPlugin, self).init()
        self.inject_js('importer_js', WPConfModifScheduleGraphic)
        self.inject_css('importer_css', WPConfModifScheduleGraphic)
        self.connect(signals.event.timetable_buttons, self.get_timetable_buttons)
        self.importer_engines = {}

    def get_blueprints(self):
        return blueprint

    def get_timetable_buttons(self, *args, **kwargs):
        yield (_('Importer'), 'create-importer-dialog')

    def get_vars_js(self):
        return {'urls': {'import_data': plugin_url_rule_to_js('importer.import_data'),
                         'importers': plugin_url_rule_to_js('importer.importers')}}

    def register_assets(self):
        self.register_js_bundle('importer_js', 'js/importer.js')
        self.register_css_bundle('importer_css', 'css/importer.css')

    def register_importer_engine(self, importer_engine, plugin):
        self.importer_engines[importer_engine._id] = (importer_engine, plugin)


blueprint = IndicoPluginBlueprint('importer', __name__)
blueprint.add_url_rule('/importers/<importer_name>/search', 'import_data', RHImportData, methods=('POST',))
blueprint.add_url_rule('/importers/', 'importers', RHGetImporters)
