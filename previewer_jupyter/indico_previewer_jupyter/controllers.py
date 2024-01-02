# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import nbformat
from flask import current_app, render_template, request, session
from flask_pluginengine import current_plugin
from nbconvert.exporters import HTMLExporter
from traitlets.config import Config
from werkzeug.exceptions import Forbidden

from indico.modules.attachments import Attachment
from indico.web.rh import RH

from indico_previewer_jupyter.cpp_highlighter import CppHighlighter


class RHEventPreviewIPyNB(RH):
    def _check_access(self):
        if not self.attachment.can_access(session.user):
            raise Forbidden

    def _process_args(self):
        self.attachment = Attachment.query.filter_by(id=request.view_args['attachment_id'], is_deleted=False).one()

    def _process(self):
        config = Config()
        config.HTMLExporter.preprocessors = [CppHighlighter]
        config.HTMLExporter.template_name = 'classic'
        # Disable unused extensions
        config.HTMLExporter.mathjax_url = ''
        config.HTMLExporter.jquery_url = ''
        config.HTMLExporter.require_js_url = ''

        with self.attachment.file.open() as f:
            notebook = nbformat.read(f, as_version=4)

        html_exporter = HTMLExporter(config=config)
        body, resources = html_exporter.from_notebook_node(notebook)
        css_code = '\n'.join(resources['inlining'].get('css', []))

        html = render_template('previewer_jupyter:ipynb_preview.html', attachment=self.attachment,
                               html_code=body, css_code=css_code, plugin=current_plugin)

        response = current_app.response_class(html)
        # Use CSP to restrict access to possibly malicious scripts or inline JS
        csp_header = "script-src 'self';"
        response.headers['Content-Security-Policy'] = csp_header
        response.headers['X-Webkit-CSP'] = csp_header
        # IE10 doesn't have proper CSP support, so we need to be more strict
        response.headers['X-Content-Security-Policy'] = 'sandbox allow-same-origin;'

        return response
