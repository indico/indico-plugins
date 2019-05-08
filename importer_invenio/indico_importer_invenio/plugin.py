# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico_importer import ImporterSourcePluginBase

from .forms import SettingsForm
from .importer import InvenioImporter


class ImporterInvenioPlugin(ImporterSourcePluginBase):
    """Importer for Invenio

    Adds Invenio importer to Indico timetable import sources.
    """
    configurable = True
    settings_form = SettingsForm
    default_settings = {'server_url': ''}
    importer_engine_classes = (InvenioImporter,)
