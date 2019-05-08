# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico_livesync import LiveSyncPluginBase
from indico_livesync_invenio.backend import InvenioLiveSyncBackend


class InvenioLiveSyncPlugin(LiveSyncPluginBase):
    """LiveSync Invenio

    Provides the Invenio backend for LiveSync
    """
    backend_classes = {'invenio': InvenioLiveSyncBackend}
