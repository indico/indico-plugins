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

import mimetypes
import re

from flask import render_template

from indico.core import signals
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.attachments.preview import Previewer

from indico_previewer_jupyter.blueprint import blueprint


def register_custom_mimetypes():
    mimetypes.add_type(b'application/x-ipynb+json', b'.ipynb')


register_custom_mimetypes()


class NotebookPreviewer(Previewer):
    ALLOWED_CONTENT_TYPE = re.compile(r"^application/x-ipynb\+json$")

    @classmethod
    def generate_content(cls, attachment):
        return render_template('previewer_jupyter:iframe_preview.html',
                               source_url=url_for_plugin('previewer_jupyter.preview_ipynb', attachment))


class JupyterPreviewerPlugin(IndicoPlugin):

    """Jupyter Notebook renderer"""

    configurable = False

    def init(self):
        super(JupyterPreviewerPlugin, self).init()
        self.connect(signals.attachments.get_file_previewers, self._get_file_previewers)

    def get_blueprints(self):
        yield blueprint

    def _get_file_previewers(self, sender, **kwargs):
        yield NotebookPreviewer
