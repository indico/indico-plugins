'''
from indico.core.plugins import IndicoPluginBlueprint
from indico_hfsummary.plugin import summarize

blueprint = IndicoPluginBlueprint('hfsummary', __name__, url_prefix='/plugin/hfsummary')
blueprint.add_url_rule('/summarize', 'summarize', summarize, methods=['POST'])

'''

