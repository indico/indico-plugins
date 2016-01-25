# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

from datetime import datetime

from flask import request, flash, redirect, jsonify, session


from indico.core import signals
from indico.core.db import db
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.core.plugins import url_for_plugin
from indico.modules.attachments.models.attachments import Attachment, AttachmentFile, AttachmentType
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.modules.events.logs import EventLogRealm, EventLogKind
from indico.util.date_time import format_date
from indico.util.fs import secure_filename

from indico_chat import _
from indico_chat.controllers.base import RHEventChatroomMixin, RHChatManageEventBase
from indico_chat.views import WPChatEventMgmt
from indico_chat.xmpp import retrieve_logs


class RHChatManageEventLogs(RHEventChatroomMixin, RHChatManageEventBase):
    """UI to retrieve logs for a chatroom"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

    def _process(self):
        if not retrieve_logs(self.chatroom):
            flash(_('There are no logs available for this room.'), 'warning')
            return redirect(url_for_plugin('.manage_rooms', self.event))
        return WPChatEventMgmt.render_template('manage_event_logs.html', self._conf, event_chatroom=self.event_chatroom,
                                               start_date=self.event.getAdjustedStartDate(),
                                               end_date=self.event.getAdjustedEndDate())


class RHChatManageEventRetrieveLogsBase(RHEventChatroomMixin, RHChatManageEventBase):
    """Retrieves logs for a chatroom"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

        if 'get_all_logs' not in request.values:
            self.start_date = datetime.strptime(request.values['start_date'], '%d/%m/%Y').date()
            self.end_date = datetime.strptime(request.values['end_date'], '%d/%m/%Y').date()
            self.date_filter = True
        else:
            self.start_date = self.end_date = None
            self.date_filter = False

    def _get_logs(self):
        return retrieve_logs(self.chatroom, self.start_date, self.end_date)


class RHChatManageEventShowLogs(RHChatManageEventRetrieveLogsBase):
    """Shows the logs for a chatroom"""

    def _process(self):
        logs = self._get_logs()
        if not logs:
            if self.date_filter:
                msg = _('Could not find any logs for the given timeframe.')
            else:
                msg = _('Could not find any logs for the chatroom.')
            return jsonify(success=False, msg=msg)
        return jsonify(success=True, html=logs, params=request.args.to_dict())


class RHChatManageEventAttachLogs(RHChatManageEventRetrieveLogsBase):
    """Attachs the logs for a chatroom to the event"""

    def _checkParams(self, params):
        RHChatManageEventRetrieveLogsBase._checkParams(self, params)
        self.material_name = request.form['material_name'].strip()
        self.file_repo_id = None

    def _process(self):
        logs = self._get_logs()
        if not logs:
            return jsonify(success=False, msg=_('No logs found'))
        self._create_material(logs)
        return jsonify(success=True)

    def _create_material(self, logs):
        folder = AttachmentFolder.find_first(object=self.event_new, is_default=False, title='Chat Logs',
                                             is_deleted=False)
        if folder is None:
            folder = AttachmentFolder(protection_mode=ProtectionMode.protected, linked_object=self.event_new,
                                      title='Chat Logs', description='Chat logs for this event')
            db.session.add(folder)

        filename = '{}.html'.format(secure_filename(self.material_name, 'logs'))
        attachment = Attachment(folder=folder, user=session.user, title=self.material_name, type=AttachmentType.file,
                                description="Chat logs for the chat room '{}'".format(self.chatroom.name))
        attachment.file = AttachmentFile(user=session.user, filename=filename, content_type='text/html')
        attachment.file.save(logs.encode('utf-8'))
        db.session.flush()
        signals.attachments.attachment_created.send(attachment, user=session.user)
        log_data = [
            ('Range', 'Everything' if not self.date_filter else
                      '{} - {}'.format(format_date(self.start_date), format_date(self.end_date))),
        ]
        self.event.log(EventLogRealm.management, EventLogKind.positive, 'Chat',
                       'Created material: {}'.format(filename), session.user, data=log_data)
