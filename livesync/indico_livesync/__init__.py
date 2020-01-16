# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core import signals
from indico.util.i18n import make_bound_gettext


_ = make_bound_gettext('livesync')
__all__ = ('LiveSyncPluginBase', 'LiveSyncBackendBase', 'AgentForm', 'SimpleChange', 'process_records',
           'MARCXMLGenerator', 'Uploader', 'MARCXMLUploader')

from .base import LiveSyncPluginBase, LiveSyncBackendBase  # isort:skip
from .forms import AgentForm  # isort:skip
from .simplify import SimpleChange, process_records  # isort:skip
from .marcxml import MARCXMLGenerator  # isort:skip
from .uploader import Uploader, MARCXMLUploader  # isort:skip


@signals.import_tasks.connect
def _import_tasks(sender, **kwargs):
    import indico_livesync.task
