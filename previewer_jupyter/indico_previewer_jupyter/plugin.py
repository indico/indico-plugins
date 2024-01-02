# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import mimetypes
import re

from flask import render_template

from indico.core import signals
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.attachments.preview import Previewer

from indico_previewer_jupyter.blueprint import blueprint


def register_custom_mimetypes():
    mimetypes.add_type('application/x-ipynb+json', '.ipynb')


register_custom_mimetypes()


class NotebookPreviewer(Previewer):
    ALLOWED_CONTENT_TYPE = re.compile(r'^application/x-ipynb\+json$')

    @classmethod
    def generate_content(cls, attachment):
        source_url = url_for_plugin('previewer_jupyter.preview_ipynb', attachment_id=attachment.id)
        return render_template('previewer_jupyter:iframe_preview.html', source_url=source_url)


class JupyterPreviewerPlugin(IndicoPlugin):

    """Jupyter Notebook renderer"""

    configurable = False

    def init(self):
        super().init()
        self.connect(signals.attachments.get_file_previewers, self._get_file_previewers)

    def get_blueprints(self):
        yield blueprint

    def _get_file_previewers(self, sender, **kwargs):
        yield NotebookPreviewer
