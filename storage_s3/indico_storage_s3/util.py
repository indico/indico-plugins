# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import unicodedata

from werkzeug.urls import url_quote


def make_content_disposition_args(attachment_filename):
    try:
        attachment_filename = attachment_filename.encode('ascii')
    except UnicodeEncodeError:
        return {
            'filename': unicodedata.normalize('NFKD', attachment_filename).encode('ascii', 'ignore'),
            'filename*': "UTF-8''%s" % url_quote(attachment_filename, safe=b''),
        }
    else:
        return {'filename': attachment_filename}
