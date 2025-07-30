from indico.core.plugins import IndicoPlugin
from indico_hfsummary.controllers import blueprint

class IndicoHFSummaryPlugin(IndicoPlugin):
    def init(self):
        super().init()
        self.blueprint = blueprint
