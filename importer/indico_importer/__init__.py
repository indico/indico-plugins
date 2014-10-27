from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, plugin_url_rule_to_js
from MaKaC.webinterface.pages.conferences import WPConfModifScheduleGraphic

from .controllers import RHDataImport, RHGetImporters


class ImporterPlugin(IndicoPlugin):
    """Importer plugin

    Extends Indico for other plugins to import data from external sources to
    the timetable.
    """

    def init(self):
        super(ImporterPlugin, self).init()
        self.inject_js('importer_js', WPConfModifScheduleGraphic)
        self.inject_css('importer_css', WPConfModifScheduleGraphic)
        self.connect(signals.timetable_buttons, self.get_timetable_buttons)
        self.importers = {}

    def get_blueprints(self):
        return blueprint

    def get_timetable_buttons(self, *args, **kwargs):
        yield ('Importer', 'createImporterDialog')

    def get_vars_js(self):
        return {'urls': {'import_data': plugin_url_rule_to_js('importer.import_data'),
                         'importers': plugin_url_rule_to_js('importer.importers')}}

    def register_assets(self):
        self.register_js_bundle('importer_js', 'js/importer.js')
        self.register_css_bundle('importer_css', 'css/importer.css')


blueprint = IndicoPluginBlueprint('importer', __name__)
blueprint.add_url_rule('/import/<importer_name>', 'import_data', RHDataImport, methods=('GET', 'POST'))
blueprint.add_url_rule('/importers', 'importers', RHGetImporters, methods=('GET', 'POST'))
