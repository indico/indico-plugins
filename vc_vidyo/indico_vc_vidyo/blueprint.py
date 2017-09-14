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

from indico_vc_vidyo.controllers import RHVidyoRoomOwner


blueprint = IndicoPluginBlueprint('vc_vidyo', 'indico_vc_vidyo')

# Room management
# using any(vidyo) instead of defaults since the event vc room locator
# includes the service and normalization skips values provided in 'defaults'
blueprint.add_url_rule('/event/<confId>/manage/videoconference/<any(vidyo):service>/<int:event_vc_room_id>/room-owner',
                       'set_room_owner', RHVidyoRoomOwner, methods=('POST',))
