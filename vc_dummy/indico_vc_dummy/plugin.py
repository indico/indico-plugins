# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from indico.core.plugins import IndicoPlugin
from indico.modules.vc import VCPluginMixin


class DummyPlugin(VCPluginMixin, IndicoPlugin):
    """Dummy

    Dummy Video conferencing plugin
    """
    configurable = True

    @property
    def logo_url(self):
        return "http://fc05.deviantart.net/fs70/f/2011/257/7/7/_dummy__vector_by_phlum-d49u7mk.png"
