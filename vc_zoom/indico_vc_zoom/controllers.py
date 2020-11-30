# This file is part of the Indico plugins.
# Copyright (C) 2020 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask import flash, jsonify, request, session
from flask_pluginengine import current_plugin
from sqlalchemy.orm.attributes import flag_modified
from webargs import fields
from webargs.flaskparser import use_kwargs

from indico.core.db import db
from indico.modules.vc.controllers import RHVCSystemEventBase
from indico.modules.vc.exceptions import VCRoomError
from indico.modules.vc.models.vc_rooms import VCRoom
from indico.web.rh import RH
from indico.util.i18n import _
from werkzeug.exceptions import Forbidden


class RHRoomHost(RHVCSystemEventBase):
    def _process(self):
        result = {}
        self.vc_room.data['host'] = session.user.identifier
        flag_modified(self.vc_room, 'data')
        try:
            self.plugin.update_room(self.vc_room, self.event)
        except VCRoomError:
            db.session.rollback()
            raise
        else:
            flash(_("You are now the host of room '{room.name}'".format(room=self.vc_room)), 'success')
            result['success'] = True
        return jsonify(result)


class RHWebhook(RH):
    CSRF_ENABLED = False

    def _check_access(self):
        token = request.headers.get('Authorization')
        expected_token = current_plugin.settings.get('webhook_token')
        if not expected_token or not token or token != expected_token:
            raise Forbidden

    @use_kwargs({
        'event': fields.String(),
        'payload': fields.Dict()
    })
    def _process(self, event, payload):
        meeting_id = payload['object']['id']
        vc_room = VCRoom.query.filter(VCRoom.data.contains({'zoom_id': meeting_id})).first()

        if not vc_room:
            # This usually happens when a room wasn't created via indico
            current_plugin.logger.debug('Action for unhandled Zoom room: %s', meeting_id)
            return

        if event in {'meeting.updated', 'webinar.updated', 'meeting.deleted', 'webinar.deleted'}:
            current_plugin.refresh_room(vc_room, None)
        else:
            current_plugin.logger.warning('Unhandled Zoom webhook payload: %s', event)
