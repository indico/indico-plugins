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

from flask import flash, jsonify, session

from indico.core.db import db
from indico.modules.vc.controllers import RHVCSystemEventBase
from indico.modules.vc.exceptions import VCRoomError
from indico.util.i18n import _


class RHVidyoRoomOwner(RHVCSystemEventBase):
    def _process(self):
        result = {}
        self.vc_room.vidyo_extension.owned_by_user = session.user
        try:
            self.plugin.update_room(self.vc_room, self.event)
        except VCRoomError as err:
            result['error'] = {'message': err.message}
            result['success'] = False
            db.session.rollback()
        else:
            flash(_("You are now the owner of the room '{room.name}'".format(room=self.vc_room)), 'success')
            result['success'] = True
        return jsonify(result)
