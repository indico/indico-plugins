# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_ai_summary.controllers import RHManageCategoryPrompts, SummarizeEvent


blueprint = IndicoPluginBlueprint('ai_summary', __name__, url_prefix='/plugin/ai-summary')

blueprint.add_url_rule('/manage-category-prompts/<int:category_id>', 'manage_category_prompts',
                       RHManageCategoryPrompts, methods=('GET', 'POST'))
blueprint.add_url_rule('/summarize-event/<int:event_id>', 'summarize_event', SummarizeEvent, methods=('POST',))
