from indico.core.plugins import IndicoPlugin
from indico_aisummary.blueprint import blueprint
from flask_pluginengine.plugin import render_plugin_template
from indico.modules.events.views import WPSimpleEventDisplay


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool"""

    def init(self):
        super().init()
        self.template_hook('event-manage-dropdown-after-notes-compile', self.summary_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPSimpleEventDisplay)

    def get_blueprints(self):
        return blueprint

    def summary_button(self, event):
        return render_plugin_template('summarize_button.html', event=event)
