from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint
from MaKaC.webinterface.pages.conferences import WPConfModifScheduleGraphic


class ImporterPlugin(IndicoPlugin):
    """Importer plugin

    Extends Indico for other plugins to import data from external sources to
    the timetable.
    """

    def init(self):
        super(ImporterPlugin, self).init()
        self.inject_js('importer_js', WPConfModifScheduleGraphic)
        self.inject_css('importer_css', WPConfModifScheduleGraphic)

    def get_blueprints(self):
        return IndicoPluginBlueprint('importer', __name__)

    def register_assets(self):
        self.register_js_bundle('importer_js', 'js/importer.js')
        self.register_css_bundle('importer_css', 'css/importer.css')
