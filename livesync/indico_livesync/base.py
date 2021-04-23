# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine import depends, trim_docstring
from sqlalchemy.orm import subqueryload

from indico.core.plugins import IndicoPlugin, PluginCategory
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.categories import Category
from indico.modules.categories.models.principals import CategoryPrincipal
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.events import Event
from indico.modules.events.notes.models.notes import EventNote
from indico.util.date_time import now_utc
from indico.util.decorators import classproperty

from indico_livesync.forms import AgentForm
from indico_livesync.initial import (apply_acl_entry_strategy, query_attachments, query_contributions, query_events,
                                     query_notes, query_subcontributions)
from indico_livesync.models.queue import LiveSyncQueueEntry
from indico_livesync.plugin import LiveSyncPlugin


@depends('livesync')
class LiveSyncPluginBase(IndicoPlugin):  # pragma: no cover
    """Base class for livesync plugins"""

    #: dict containing the backend(s) provided by the plugin; the keys are unique identifiers
    backend_classes = None
    category = PluginCategory.synchronization

    def init(self):
        super().init()
        for name, backend_class in self.backend_classes.items():
            assert backend_class.plugin is None
            backend_class.plugin = type(self)
            LiveSyncPlugin.instance.register_backend_class(name, backend_class)


class LiveSyncBackendBase:
    """Base class for livesync backends"""

    #: the plugin containing the agent
    plugin = None  # set automatically when the agent is registered
    #: the Uploader to use. only needed if run and run_initial_export are not overridden
    uploader = None
    #: the form used when creating/editing the agent
    form = AgentForm
    #: whether only one agent with this backend is allowed
    unique = False

    @classproperty
    @classmethod
    def title(cls):
        parts = trim_docstring(cls.__doc__).split('\n', 1)
        return parts[0].strip()

    @classproperty
    @classmethod
    def description(cls):
        parts = trim_docstring(cls.__doc__).split('\n', 1)
        try:
            return parts[1].strip()
        except IndexError:
            return 'no description available'

    def __init__(self, agent):
        """
        :param agent: a `LiveSyncAgent` instance
        """
        self.agent = agent

    def fetch_records(self, count=None):
        query = (self.agent.queue
                 .filter_by(processed=False)
                 .order_by(LiveSyncQueueEntry.timestamp)
                 .limit(count))
        return query.all()

    def update_last_run(self):
        """Updates the last run timestamp.

        Don't forget to call this if you implement your own `run` method!
        """
        self.agent.last_run = now_utc()

    def run(self):
        """Runs the livesync export"""
        if self.uploader is None:  # pragma: no cover
            raise NotImplementedError

        records = self.fetch_records()
        uploader = self.uploader(self)
        LiveSyncPlugin.logger.info('Uploading %d records', len(records))
        uploader.run(records)
        self.update_last_run()

    def run_initial_export(self, batch_size=5000, force=False):
        """Runs the initial export.

        This process is expected to take a very long time.
        """
        if self.uploader is None:  # pragma: no cover
            raise NotImplementedError

        uploader = self.uploader(self)

        Category.allow_relationship_preloading = True
        Category.preload_relationships(Category.query, 'acl_entries',
                                       strategy=lambda rel: apply_acl_entry_strategy(subqueryload(rel),
                                                                                     CategoryPrincipal))
        _category_cache = Category.query.all()  # noqa: F841

        events = query_events()
        if not force:
            events = events.filter(~Event.citadel_es_entries.any())
        uploader.run_initial(events.yield_per(batch_size), events.count())

        contributions = query_contributions()
        if not force:
            contributions = contributions.filter(~Contribution.citadel_es_entries.any())
        uploader.run_initial(contributions.yield_per(batch_size), contributions.count())

        subcontributions = query_subcontributions()
        if not force:
            subcontributions = subcontributions.filter(~SubContribution.citadel_es_entries.any())
        uploader.run_initial(subcontributions.yield_per(batch_size), subcontributions.count())

        attachments = query_attachments()
        if not force:
            attachments = attachments.filter(~Attachment.citadel_es_entries.any())
        uploader.run_initial(attachments.yield_per(batch_size), attachments.count())

        notes = query_notes()
        if not force:
            notes = notes.filter(~EventNote.citadel_es_entries.any())
        uploader.run_initial(notes.yield_per(batch_size), notes.count())
