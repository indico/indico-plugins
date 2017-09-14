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

from flask import render_template
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import CppLexer, JavaLexer, PhpLexer, RubyLexer, get_lexer_for_mimetype

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.modules.attachments.preview import Previewer


def register_custom_mimetypes():
    mimetypes.add_type(b'text/x-csharp', b'.cs')


register_custom_mimetypes()


class PygmentsPreviewer(Previewer):
    # All supported MIME types
    MIMETYPES = ('text/css', 'text/x-python', 'text/x-ruby-script', 'text/x-java-source', 'text/x-c',
                 'application/javascript', 'text/x-c', 'text/x-fortran', 'text/x-csharp', 'text/php',
                 'text/x-php')

    # Python's mimetypes lib and Pygments do not quite agree on some MIME types
    CUSTOM_LEXERS = {
        'text/x-c': CppLexer(),
        'text/x-java-source': JavaLexer(),
        'text/x-ruby-script': RubyLexer(),
        'text/php': PhpLexer()
    }

    @classmethod
    def can_preview(cls, attachment_file):
        return attachment_file.content_type in cls.MIMETYPES

    @classmethod
    def generate_content(cls, attachment):
        mime_type = attachment.file.content_type

        lexer = cls.CUSTOM_LEXERS.get(mime_type)
        if lexer is None:
            lexer = get_lexer_for_mimetype(mime_type)

        with attachment.file.open() as f:
            html_formatter = HtmlFormatter(style='tango', linenos='inline', prestyles='mono')
            html_code = highlight(f.read(), lexer, html_formatter)

        css_code = html_formatter.get_style_defs('.highlight')

        return render_template('previewer_code:pygments_preview.html', attachment=attachment,
                               html_code=html_code, css_code=css_code)


class CodePreviewerPlugin(IndicoPlugin):
    """Syntax highlighter (Pygments)"""

    configurable = False

    def init(self):
        super(CodePreviewerPlugin, self).init()
        self.connect(signals.attachments.get_file_previewers, self._get_file_previewers)

    def _get_file_previewers(self, sender, **kwargs):
        yield PygmentsPreviewer
