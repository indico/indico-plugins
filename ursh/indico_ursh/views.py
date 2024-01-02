# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import WPJinjaMixinPlugin
from indico.web.views import WPDecorated


class WPShortenURLPage(WPJinjaMixinPlugin, WPDecorated):
    def _get_body(self, params):
        return self._get_page_content(params)
