# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
