from indico.core.plugins import IndicoPluginBlueprint
from indico_hfsummary.controllers import SummarizeEvent

blueprint = IndicoPluginBlueprint('hfsummary', __name__, url_prefix='/plugin/hfsummary')

blueprint.add_url_rule('/summarize-event/<int:event_id>', 'summarize_event', SummarizeEvent, methods=('GET',))


