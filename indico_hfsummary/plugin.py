from indico.core.plugins import IndicoPlugin
from indico_hfsummary.blueprint import blueprint
from flask_pluginengine.plugin import render_plugin_template

class IndicoHFSummaryPlugin(IndicoPlugin):
    '''
    AI-assisted minutes summarization tool
    
    '''
    
    def init(self):
        super().init()
        self.template_hook('event-manage-button', self.summary_button)

    def get_blueprints(self):
        return blueprint
    
    def summary_button(self, event):
        print("work damn you")
        return render_plugin_template('indico_hfsummary/summarize_button.html', event = event)