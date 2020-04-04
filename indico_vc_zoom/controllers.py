

from __future__ import unicode_literals

from flask import flash, jsonify, session

from indico.core.db import db
from indico.modules.vc.controllers import RHVCSystemEventBase
from indico.modules.vc.exceptions import VCRoomError
from indico.util.i18n import _


class RHZoomRoomOwner(RHVCSystemEventBase):
    def _process(self):
        result = {}
        self.vc_room.zoom_meeting.owned_by_user = session.user
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
