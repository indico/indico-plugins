from indico.core.plugins import IndicoPluginBlueprint
from indico_hfsummary.controllers import Summarizer
from indico_hfsummary.controllers import SummarizeEvent

blueprint = IndicoPluginBlueprint('indico_hfsummary', __name__, url_prefix='/plugin/hfsummary')

blueprint.add_url_rule('/summarize', 'summarize', Summarizer, methods=('POST','GET'))

blueprint.add_url_rule('/summarize-event/<int:event_id>', 'summarize_event', SummarizeEvent, methods=('GET',))
