

from flask import request

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus
from indico.web.http_api.hooks.base import HTTPAPIHook


class DeleteVCRoomAPI(HTTPAPIHook):
    PREFIX = 'api'
    TYPES = ('deletevcroom',)
    RE = r'zoom'
    GUEST_ALLOWED = False
    VALID_FORMATS = ('json',)
    COMMIT = True
    HTTP_POST = True

    def _has_access(self, user):
        from indico_vc_zoom.plugin import ZoomPlugin
        return user in ZoomPlugin.settings.acls.get('managers')

    def _getParams(self):
        super(DeleteVCRoomAPI, self)._getParams()
        self._room_ids = map(int, request.form.getlist('rid'))

    def api_deletevcroom(self, user):
        from indico_vc_zoom.plugin import ZoomPlugin
        from indico_vc_zoom.api import APIException

        success = []
        failed = []
        not_in_db = []

        for rid in self._room_ids:
            room = VCRoom.query.filter(VCRoom.type == 'zoom',
                                       VCRoom.status == VCRoomStatus.created,
                                       VCRoom.data.contains({'zoom_id': str(rid)})).first()
            if not room:
                not_in_db.append(rid)
                continue
            try:
                room.plugin.delete_meeting(room, None)
            except APIException:
                failed.append(rid)
                ZoomPlugin.logger.exception('Could not delete VC room %s', room)
            else:
                room.status = VCRoomStatus.deleted
                success.append(rid)
                ZoomPlugin.logger.info('%s deleted', room)

        return {'success': success, 'failed': failed, 'missing': not_in_db}
