# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import flash, jsonify, request, session
from flask_pluginengine import current_plugin
from marshmallow import EXCLUDE
from sqlalchemy.orm.attributes import flag_modified
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import Forbidden

from indico.core.db import db
from indico.core.errors import UserValueError
from indico.modules.vc.controllers import RHVCSystemEventBase
from indico.modules.vc.exceptions import VCRoomError, VCRoomNotFoundError
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus
from indico.util.i18n import _
from indico.web.rh import RH


class RHRoomAlternativeHost(RHVCSystemEventBase):
    def _process(self):
        new_identifier = session.user.identifier
        if new_identifier == self.vc_room.data['host'] or new_identifier in self.vc_room.data['alternative_hosts']:
            flash(_('You were already an (alternative) host of this meeting'), 'warning')
            return jsonify(success=False)

        try:
            self.plugin.refresh_room(self.vc_room, self.event)
            self.vc_room.data['alternative_hosts'].append(new_identifier)
            flag_modified(self.vc_room, 'data')
            self.plugin.update_room(self.vc_room, self.event)
        except VCRoomNotFoundError as exc:
            db.session.rollback()
            raise UserValueError(str(exc)) from exc
        except VCRoomError:
            db.session.rollback()
            raise
        else:
            flash(_("You are now an alternative host of room '{room}'").format(room=self.vc_room.name), 'success')
        return jsonify(success=True)


class RHWebhook(RH):
    CSRF_ENABLED = False

    def _check_access(self):
        token = request.headers.get('Authorization')
        expected_token = current_plugin.settings.get('webhook_token')
        if not expected_token or not token or token != expected_token:
            raise Forbidden

    @use_kwargs({
        'event': fields.String(required=True),
        'payload': fields.Dict(required=True)
    }, unknown=EXCLUDE)
    def _process(self, event, payload):
        meeting_id = payload['object']['id']
        vc_room = VCRoom.query.filter(VCRoom.data.contains({'zoom_id': meeting_id})).first()

        if not vc_room:
            # This usually happens when a room wasn't created via indico
            current_plugin.logger.debug('Action for unhandled Zoom room: %s', meeting_id)
            return

        if event in ('meeting.updated', 'webinar.updated'):
            current_plugin.refresh_room(vc_room, None)
        elif event in ('meeting.deleted', 'webinar.deleted'):
            current_plugin.logger.info('Zoom room deleted: %s', meeting_id)
            vc_room.status = VCRoomStatus.deleted
        else:
            current_plugin.logger.warning('Unhandled Zoom webhook payload: %s', event)
