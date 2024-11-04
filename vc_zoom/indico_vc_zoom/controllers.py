# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2024 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import hashlib
import hmac

from flask import jsonify, request, session
from flask_pluginengine import current_plugin
from marshmallow import EXCLUDE
from sqlalchemy.orm.attributes import flag_modified
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import Forbidden, ServiceUnavailable

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
            raise UserValueError(_('You were already an (alternative) host of this meeting'))

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
        return '', 204


class RHWebhook(RH):
    CSRF_ENABLED = False

    def _is_validation_event(self, event):
        return event == 'endpoint.url_validation'

    def _get_hmac(self, data):
        webhook_token = current_plugin.settings.get('webhook_token')
        if not webhook_token:
            current_plugin.logger.warning('Tried to validate Zoom webhook, but no secret token has been configured')
            raise ServiceUnavailable('No Zoom Webhook Secret Token configured')
        return hmac.new(webhook_token.encode(), data, hashlib.sha256).hexdigest()

    def _check_access(self):
        timestamp = request.headers.get('x-zm-request-timestamp')
        zoom_signature_header = request.headers.get('x-zm-signature')
        signature = self._get_hmac(b'v0:%s:%s' % (timestamp.encode(), request.data))
        expected_header = f'v0={signature}'
        if zoom_signature_header != expected_header:
            current_plugin.logger.warning('Received request with invalid signature: Expected %s, got %s, payload %s',
                                          expected_header, zoom_signature_header, request.data.decode())
            raise Forbidden('Zoom signature verification failed')

    @use_kwargs({
        'event': fields.String(required=True),
        'payload': fields.Dict(required=True)
    }, unknown=EXCLUDE)
    def _process(self, event, payload):
        if self._is_validation_event(event):
            return self._handle_validation(payload)
        return self._handle_zoom_event(event, payload)

    def _handle_validation(self, payload):
        plain_token = payload['plainToken']
        signed_token = self._get_hmac(plain_token.encode())
        return jsonify({
            'plainToken': plain_token,
            'encryptedToken': signed_token
        })

    def _handle_zoom_event(self, event, payload):
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
