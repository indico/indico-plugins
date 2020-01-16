# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico_livesync import LiveSyncPluginBase
from indico_livesync_debug.backend import LiveSyncDebugBackend


class LiveSyncDebugPlugin(LiveSyncPluginBase):
    """LiveSync Debug

    Provides the debug backend for LiveSync which just prints/logs changes
    """
    backend_classes = {'debug': LiveSyncDebugBackend}
