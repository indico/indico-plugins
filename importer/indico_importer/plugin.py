# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, PluginCategory, plugin_url_rule_to_js
from indico.modules.events.timetable.views import WPManageTimetable
from indico.web.flask.util import url_rule_to_js

from indico_importer import _
from indico_importer.controllers import RHBlockEndTime, RHDayEndTime, RHGetImporters, RHImportData


class ImporterPlugin(IndicoPlugin):
    """Importer

    Extends Indico for other plugins to import data from external sources to
    the timetable.
    """
    category = PluginCategory.importers

    def init(self):
        super(ImporterPlugin, self).init()
        self.inject_bundle('main.js', WPManageTimetable)
        self.inject_bundle('main.css', WPManageTimetable)
        self.connect(signals.event.timetable_buttons, self.get_timetable_buttons)
        self.importer_engines = {}

    def get_blueprints(self):
        return blueprint

    def get_timetable_buttons(self, *args, **kwargs):
        if self.importer_engines:
            yield _('Importer'), 'create-importer-dialog'

    def get_vars_js(self):
        return {'urls': {'import_data': plugin_url_rule_to_js('importer.import_data'),
                         'importers': plugin_url_rule_to_js('importer.importers'),
                         'day_end_date': plugin_url_rule_to_js('importer.day_end_date'),
                         'block_end_date': plugin_url_rule_to_js('importer.block_end_date'),
                         'add_contrib': url_rule_to_js('timetable.add_contribution'),
                         'create_subcontrib_rest': url_rule_to_js('contributions.create_subcontrib_rest'),
                         'create_contrib_reference_rest': url_rule_to_js('contributions.create_contrib_reference_rest'),
                         'create_subcontrib_reference_rest': url_rule_to_js('contributions'
                                                                            '.create_subcontrib_reference_rest'),
                         'add_link': url_rule_to_js('attachments.add_link')}}

    def register_importer_engine(self, importer_engine, plugin):
        self.importer_engines[importer_engine._id] = (importer_engine, plugin)


blueprint = IndicoPluginBlueprint('importer', __name__)
blueprint.add_url_rule('/importers/<importer_name>/search', 'import_data', RHImportData, methods=('POST',))
blueprint.add_url_rule('/importers/', 'importers', RHGetImporters)

blueprint.add_url_rule('/importers/<importer_name>/event/<confId>/day-end-date', 'day_end_date', RHDayEndTime)
blueprint.add_url_rule('/importers/<importer_name>/event/<confId>/entry/<entry_id>/block-end-date', 'block_end_date',
                       RHBlockEndTime)
