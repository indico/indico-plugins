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

from flask import request

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus
from indico.web.http_api.hooks.base import HTTPAPIHook


class DeleteVCRoomAPI(HTTPAPIHook):
    PREFIX = 'api'
    TYPES = ('deletevcroom',)
    RE = r'vidyo'
    GUEST_ALLOWED = False
    VALID_FORMATS = ('json',)
    COMMIT = True
    HTTP_POST = True

    def _has_access(self, user):
        from indico_vc_vidyo.plugin import VidyoPlugin
        return user in VidyoPlugin.settings.acls.get('managers')

    def _getParams(self):
        super(DeleteVCRoomAPI, self)._getParams()
        self._room_ids = map(int, request.form.getlist('rid'))

    def api_deletevcroom(self, user):
        from indico_vc_vidyo.plugin import VidyoPlugin
        from indico_vc_vidyo.api import APIException

        success = []
        failed = []
        not_in_db = []

        for rid in self._room_ids:
            room = VCRoom.query.filter(VCRoom.type == 'vidyo',
                                       VCRoom.status == VCRoomStatus.created,
                                       VCRoom.data.contains({'vidyo_id': str(rid)})).first()
            if not room:
                not_in_db.append(rid)
                continue
            try:
                room.plugin.delete_room(room, None)
            except APIException:
                failed.append(rid)
                VidyoPlugin.logger.exception('Could not delete VC room %s', room)
            else:
                room.status = VCRoomStatus.deleted
                success.append(rid)
                VidyoPlugin.logger.info('%s deleted', room)

        return {'success': success, 'failed': failed, 'missing': not_in_db}
