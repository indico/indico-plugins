# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import mimetypes

import requests
from flask import flash, session
from flask_pluginengine import current_plugin, render_plugin_template

from indico.core import signals
from indico.core.db import db
from indico.modules.attachments.controllers.management.base import (_get_folders_protection_info,
                                                                    _render_attachment_list, _render_protection_message)
from indico.modules.attachments.controllers.management.category import RHCategoryAttachmentManagementBase
from indico.modules.attachments.controllers.management.event import RHEventAttachmentManagementBase
from indico.modules.attachments.models.attachments import Attachment, AttachmentFile, AttachmentType
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.util.fs import secure_client_filename
from indico.web.util import jsonify_data, jsonify_template

from indico_owncloud import _
from indico_owncloud.forms import AddAttachmentOwncloudForm


class AddAttachmentOwncloudMixin:
    """Add cloud storage attachment."""

    def _process(self):
        form = AddAttachmentOwncloudForm(linked_object=self.object)
        if form.validate_on_submit():
            files = form.data['owncloud_filepicker']['files']
            folder = form.data['folder'] or AttachmentFolder.get_or_create_default(linked_object=self.object)
            for f in files:
                filename = f.split('/')[-1].split('?')[0]
                local_filename = secure_client_filename(filename)
                attachment = Attachment(folder=folder, user=session.user, title=local_filename,
                                        type=AttachmentType.file, protection_mode=form.data['protection_mode'])
                if attachment.is_self_protected:
                    attachment.acl = form.data['acl']
                content_type = mimetypes.guess_type(local_filename)[0] or 'application/octet-stream'
                attachment.file = AttachmentFile(user=session.user, filename=local_filename, content_type=content_type)

                file_response = requests.get(f)
                file_response.raise_for_status()
                attachment.file.save(file_response.content)

                db.session.add(attachment)
                db.session.flush()
                current_plugin.logger.info('Attachment %s uploaded by %s', attachment, session.user)
                signals.attachments.attachment_created.send(attachment, user=session.user)
            flash(_('Attachment added'))
            return jsonify_data(attachment_list=_render_attachment_list(self.object))
        return jsonify_template('add_owncloud_files.html', _render_func=render_plugin_template, form=form,
                                protection_message=_render_protection_message(self.object),
                                folders_protection_info=_get_folders_protection_info(self.object))


class RHAddCategoryAttachmentOwncloud(AddAttachmentOwncloudMixin, RHCategoryAttachmentManagementBase):
    pass


class RHAddEventAttachmentOwncloud(AddAttachmentOwncloudMixin, RHEventAttachmentManagementBase):
    pass
