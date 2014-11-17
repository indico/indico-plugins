# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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
from wtforms.validators import DataRequired, URL

from indico.util.i18n import _
from indico.util.string import strip_whitespace

from indico_livesync import LiveSyncAgentBase, MARCXMLUploader, AgentForm


class InvenioAgentForm(AgentForm):
    server_url = URLField(_('URL'), [DataRequired(), URL(require_tld=False)], filters=[strip_whitespace],
                          description=_("The URL of the Invenio instance"))


class InvenioUploader(MARCXMLUploader):
    def upload_xml(self, xml):
        pass


class InvenioLiveSyncAgent(LiveSyncAgentBase):
    """Invenio Agent

    This agent uploads data to Invenio.
    """

    uploader = InvenioUploader
    form = InvenioAgentForm
