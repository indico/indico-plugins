# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core import signals
from indico.util.i18n import make_bound_gettext


_ = make_bound_gettext('livesync')
__all__ = ('LiveSyncPluginBase', 'LiveSyncBackendBase', 'AgentForm', 'SimpleChange', 'process_records',
           'Uploader')


from .base import LiveSyncBackendBase, LiveSyncPluginBase  # noqa: E402
from .forms import AgentForm  # noqa: E402
from .simplify import SimpleChange, process_records  # noqa: E402
from .uploader import Uploader  # noqa: E402


@signals.core.import_tasks.connect
def _import_tasks(sender, **kwargs):
    import indico_livesync.task  # noqa: F401
