
from indico.core.plugins import IndicoPluginBlueprint


blueprint = IndicoPluginBlueprint('hfsummary', __name__, url_prefix='/plugin/hfsummary')

from indico_hfsummary.controllers import summarize

blueprint.add_url_rule('/summarize', 'summarize', summarize, methods=['POST'])



