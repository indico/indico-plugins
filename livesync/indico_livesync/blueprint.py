# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_livesync.controllers import RHAddAgent, RHDeleteAgent, RHEditAgent


blueprint = IndicoPluginBlueprint('livesync', 'indico_livesync', url_prefix='/admin/plugins/livesync')

blueprint.add_url_rule('/agents/create/<backend>', 'add_agent', RHAddAgent, methods=('GET', 'POST'))
blueprint.add_url_rule('/agents/<int:agent_id>', 'edit_agent', RHEditAgent, methods=('GET', 'POST'))
blueprint.add_url_rule('/agents/<int:agent_id>', 'delete_agent', RHDeleteAgent, methods=('DELETE',))
