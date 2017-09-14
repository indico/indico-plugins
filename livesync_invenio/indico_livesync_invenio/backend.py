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
