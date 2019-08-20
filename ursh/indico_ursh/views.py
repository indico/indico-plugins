# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import WPJinjaMixinPlugin
from indico.web.views import WPDecorated


class WPShortenURLPage(WPJinjaMixinPlugin, WPDecorated):
    def _get_body(self, params):
        return self._get_page_content(params)
