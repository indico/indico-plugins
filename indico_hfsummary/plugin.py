from indico.core.plugins import IndicoPlugin
from indico_hfsummary.blueprint import blueprint

class IndicoHFSummaryPlugin(IndicoPlugin):
    def init(self):
        super().init()
        self.blueprint = blueprint

    def get_blueprints(self):
        return blueprint