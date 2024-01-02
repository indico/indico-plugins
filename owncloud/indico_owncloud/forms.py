# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms import Field
from wtforms.validators import DataRequired, ValidationError

from indico.core.config import config
from indico.modules.attachments.forms import AttachmentFormBase
from indico.util.i18n import _
from indico.web.forms.widgets import JinjaWidget

from indico_owncloud.util import get_filepicker_url


class IndicoOwncloudField(Field):
    widget = JinjaWidget('owncloud_filepicker_widget.html', plugin='owncloud', single_line=True, single_kwargs=True)

    def __init__(self, label=None, validators=None, **kwargs):
        super().__init__(label, validators, **kwargs)
        self.filepicker_url = get_filepicker_url()
        self.origin = config.BASE_URL

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = {'files': [f.rstrip() for f in valuelist[0].split('\n')]}


class AttachmentOwncloudFormMixin:
    owncloud_filepicker = IndicoOwncloudField(_('Files'), [DataRequired()])

    def validate_owncloud_filepicker(self, field):
        if self.owncloud_filepicker.data and self.owncloud_filepicker.data['files'] == ['']:
            raise ValidationError('Select some files')


class AddAttachmentOwncloudForm(AttachmentOwncloudFormMixin, AttachmentFormBase):
    pass


class EditAttachmentOwncloudForm(AttachmentOwncloudFormMixin, AttachmentFormBase):
    pass
