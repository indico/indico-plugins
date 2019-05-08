# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
