# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_livesync.controllers import RHAddAgent, RHDeleteAgent, RHEditAgent


blueprint = IndicoPluginBlueprint('livesync', 'indico_livesync', url_prefix='/admin/plugins/livesync')

blueprint.add_url_rule('/agents/create/<backend>', 'add_agent', RHAddAgent, methods=('GET', 'POST'))
blueprint.add_url_rule('/agents/<int:agent_id>', 'edit_agent', RHEditAgent, methods=('GET', 'POST'))
blueprint.add_url_rule('/agents/<int:agent_id>', 'delete_agent', RHDeleteAgent, methods=('DELETE',))
