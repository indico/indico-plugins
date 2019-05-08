# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import WPJinjaMixinPlugin
from indico.modules.events.management.views import WPEventManagement


class WPStatistics(WPJinjaMixinPlugin, WPEventManagement):
    sidemenu_option = 'statistics'
