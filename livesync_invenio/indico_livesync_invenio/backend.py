# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from wtforms.fields.html5 import URLField
from wtforms.validators import URL, DataRequired

from indico_livesync import AgentForm, LiveSyncBackendBase, MARCXMLUploader
from indico_livesync_invenio import _
from indico_livesync_invenio.connector import InvenioConnector


class InvenioAgentForm(AgentForm):
    server_url = URLField(_('URL'), [DataRequired(), URL(require_tld=False)],
                          description=_("The URL of the Invenio instance"))


class InvenioUploaderError(Exception):
    pass


class InvenioUploader(MARCXMLUploader):
    def __init__(self, *args, **kwargs):
        super(InvenioUploader, self).__init__(*args, **kwargs)
        url = self.backend.agent.settings.get('server_url')
        self.connector = InvenioConnector(url)

    def upload_xml(self, xml):
        result = self.connector.upload_marcxml(xml, '-ir').read()
        if not isinstance(result, long) and not result.startswith('[INFO]'):
            raise InvenioUploaderError(result.strip())


class InvenioLiveSyncBackend(LiveSyncBackendBase):
    """Invenio

    This backend uploads data to Invenio.
    """

    uploader = InvenioUploader
    form = InvenioAgentForm
