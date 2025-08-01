
from indico.core.plugins import IndicoPluginBlueprint


blueprint = IndicoPluginBlueprint('indico_hfsummary', __name__, url_prefix='/plugin/hfsummary')

from indico_hfsummary.controllers import Summarizer

blueprint.add_url_rule('/summarize', 'summarize', Summarizer, methods=('POST','GET'))



