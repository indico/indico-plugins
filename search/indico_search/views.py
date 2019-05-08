# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import WPJinjaMixinPlugin
from indico.modules.categories.views import WPCategory
from indico.modules.events.views import WPConferenceDisplayBase


class WPSearchCategory(WPJinjaMixinPlugin, WPCategory):
    pass


class WPSearchConference(WPJinjaMixinPlugin, WPConferenceDisplayBase):
    pass
