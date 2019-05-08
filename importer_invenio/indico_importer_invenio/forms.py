# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from wtforms.fields.html5 import URLField
from wtforms.validators import URL

from indico.web.forms.base import IndicoForm

from indico_importer_invenio import _


class SettingsForm(IndicoForm):
    server_url = URLField(_("Invenio server URL"), validators=[URL()])
