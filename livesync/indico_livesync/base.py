# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
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
from indico_livesync.models.queue import EntryType, LiveSyncQueueEntry
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
    #: whether a reset can delete data on whatever backend is used as well or the user
    #: needs to do it themself after doing a reset
    reset_deletes_indexed_data = False

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

    def is_configured(self):
        """Check whether the backend is properly configured.

        If this returns False, running the initial export or queue
        will not be possible.
        """
        return True

    def check_queue_status(self):
        """Return whether queue runs are allowed (or why not).

        :return: ``allowed, reason`` tuple; the reason is None if runs are allowed.
        """
        if not self.is_configured():
            return False, 'not configured'
        if self.agent.initial_data_exported:
            return True, None
        return False, 'initial export not performed'

    def fetch_records(self, allowed_categories=()):
        query = (self.agent.queue
                 .filter(~LiveSyncQueueEntry.processed)
                 .order_by(LiveSyncQueueEntry.timestamp))
        if LiveSyncPlugin.settings.get('skip_category_changes'):
            LiveSyncPlugin.logger.warning('Category changes are currently being skipped')
            whitelist_filter = False
            if allowed_categories:
                whitelist_filter = LiveSyncQueueEntry.category_id.in_(allowed_categories)
            query = query.filter((LiveSyncQueueEntry.type != EntryType.category) | whitelist_filter)
        return query.all()

    def update_last_run(self):
        """Updates the last run timestamp.

        Don't forget to call this if you implement your own `run` method!
        """
        self.agent.last_run = now_utc()

    def process_queue(self, uploader, allowed_categories=()):
        """Process queued entries during an export run."""
        records = self.fetch_records(allowed_categories)
        LiveSyncPlugin.logger.info(f'Uploading %d records via {self.uploader.__name__}', len(records))
        uploader.run(records)

    def run(self, verbose=False, from_cli=False, allowed_categories=()):
        """Runs the livesync export"""
        if self.uploader is None:  # pragma: no cover
            raise NotImplementedError

        uploader = self.uploader(self, verbose=verbose, from_cli=from_cli)
        self._precache_categories()
        self.process_queue(uploader, allowed_categories)
        self.update_last_run()

    def get_initial_query(self, model_cls, force):
        """Get the initial export query for a given model.

        Supported models are `Event`, `Contribution`, `SubContribution`,
        `Attachment` and `EventNote`.

        :param model_cls: The model class to query
        :param force: Whether the initial export was started with ``--force``
        """
        fn = {
            Event: query_events,
            Contribution: query_contributions,
            SubContribution: query_subcontributions,
            Attachment: query_attachments,
            EventNote: query_notes,
        }[model_cls]
        return fn()

    def get_data_query(self, model_cls, ids):
        """Get the export query for a given model and set of ids.

        Supported models are `Event`, `Contribution`, `SubContribution`,
        `Attachment` and `EventNote`.

        This is very similar to `get_initial_query` except that it will only
        export the specified records.

        :param model_cls: The model class to query
        :param ids: A collection of ids to query
        """
        fn = {
            Event: query_events,
            Contribution: query_contributions,
            SubContribution: query_subcontributions,
            Attachment: query_attachments,
            EventNote: query_notes,
        }[model_cls]
        return fn(ids=ids)

    def run_initial_export(self, batch_size, force=False, verbose=False):
        """Runs the initial export.

        This process is expected to take a very long time.
        :return: True if everything was successful, False if not
        """
        if self.uploader is None:  # pragma: no cover
            raise NotImplementedError

        uploader = self.uploader(self, verbose=verbose, from_cli=True)
        self._precache_categories()

        events = self.get_initial_query(Event, force)
        contributions = self.get_initial_query(Contribution, force)
        subcontributions = self.get_initial_query(SubContribution, force)
        attachments = self.get_initial_query(Attachment, force)
        notes = self.get_initial_query(EventNote, force)

        print('Exporting events')
        if not uploader.run_initial(events.yield_per(batch_size), events.count()):
            print('Initial export of events failed')
            return False
        print('Exporting contributions')
        if not uploader.run_initial(contributions.yield_per(batch_size), contributions.count()):
            print('Initial export of contributions failed')
            return False
        print('Exporting subcontributions')
        if not uploader.run_initial(subcontributions.yield_per(batch_size), subcontributions.count()):
            print('Initial export of subcontributions failed')
            return False
        print('Exporting attachments')
        if not uploader.run_initial(attachments.yield_per(batch_size), attachments.count()):
            print('Initial export of attachments failed')
            return False
        print('Exporting notes')
        if not uploader.run_initial(notes.yield_per(batch_size), notes.count()):
            print('Initial export of notes failed')
            return False
        return True

    def check_reset_status(self):
        """Return whether a reset is allowed (or why not).

        When resetting is not allowed, the message indicates why this is the case.

        :return: ``allowed, reason`` tuple; the reason is None if resetting is allowed.
        """
        if not self.agent.queue.has_rows() and not self.agent.initial_data_exported:
            return False, 'There is nothing to reset'
        return True, None

    def reset(self):
        """Perform a full reset of all data related to the backend.

        This deletes all queued changes, resets the initial export state back
        to pending and do any other backend-specific tasks that may be required.

        It is not necessary to delete the actual search indexes (which are possibly
        on a remote service), but if your backend has the ability to do it you may
        want to do it and display a message to the user indicating this.
        """
        self.agent.initial_data_exported = False
        self.agent.queue.delete()

    def _precache_categories(self):
        Category.allow_relationship_preloading = True
        Category.preload_relationships(Category.query, 'acl_entries',
                                       strategy=lambda rel: apply_acl_entry_strategy(subqueryload(rel),
                                                                                     CategoryPrincipal))
        self._category_cache = Category.query.all()
