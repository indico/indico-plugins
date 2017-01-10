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

from flask_pluginengine import current_plugin

from indico_importer import ImporterEngineBase

from .connector import InvenioConnector
from .converters import InvenioRecordConverter


class InvenioImporter(ImporterEngineBase):
    """Fetches and converts data from CDS Invenio"""

    _id = 'invenio'
    name = 'CDS Invenio'

    def import_data(self, query, size):
        url = current_plugin.settings.get('server_url')
        registers = InvenioConnector(url).search(p=query, rg=size)
        return InvenioRecordConverter.convert(registers)
