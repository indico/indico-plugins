# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import unicodedata
from urllib.parse import quote


def make_content_disposition_args(attachment_filename):
    try:
        attachment_filename.encode('ascii')
    except UnicodeEncodeError:
        simple = unicodedata.normalize('NFKD', attachment_filename)
        simple = simple.encode('ascii', 'ignore').decode('ascii')
        # safe = RFC 5987 attr-char
        quoted = quote(attachment_filename, safe='!#$&+-.^_`|~')
        return {'filename': simple, 'filename*': f"UTF-8''{quoted}"}
    else:
        return {'filename': attachment_filename}
