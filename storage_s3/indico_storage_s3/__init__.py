from __future__ import unicode_literals

from indico.core import signals


@signals.import_tasks.connect
def _import_tasks(sender, **kwargs):
    import indico_storage_s3.task
