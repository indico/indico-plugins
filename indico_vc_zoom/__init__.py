from __future__ import unicode_literals

from indico.core import signals
from indico.util.i18n import make_bound_gettext


_ = make_bound_gettext('vc_zoom')


@signals.import_tasks.connect
def _import_tasks(sender, **kwargs):
    import indico_vc_zoom.task
