# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.
import time

import click
from flask_pluginengine import current_plugin
from sqlalchemy.orm import selectinload, undefer, joinedload, subqueryload, contains_eager
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.core.db import db
from indico.core.db.sqlalchemy.links import LinkType
from indico.modules.attachments import Attachment, AttachmentFolder
from indico.modules.attachments.models.principals import AttachmentPrincipal, AttachmentFolderPrincipal
from indico.modules.categories import Category
from indico.modules.categories.models.principals import CategoryPrincipal
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.principals import ContributionPrincipal
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.principals import EventPrincipal
from indico.modules.events.notes.models.notes import EventNote, EventNoteRevision
from indico.modules.events.sessions import Session
from indico.modules.events.sessions.models.principals import SessionPrincipal
from indico.util.console import cformat
from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='livesync')
def cli():
    """Manage the LiveSync plugin."""


@cli.command()
def available_backends():
    """Lists the currently available backend types"""
    print('The following LiveSync agents are available:')
    for name, backend in current_plugin.backend_classes.items():
        print(cformat('  - %{white!}{}%{reset}: {} ({})').format(name, backend.title, backend.description))


@cli.command()
def agents():
    """Lists the currently active agents"""
    print('The following LiveSync agents are active:')
    agent_list = LiveSyncAgent.query.order_by(LiveSyncAgent.backend_name, db.func.lower(LiveSyncAgent.name)).all()
    table_data = [['ID', 'Name', 'Backend', 'Initial Export', 'Queue']]
    for agent in agent_list:
        initial = (cformat('%{green!}done%{reset}') if agent.initial_data_exported else
                   cformat('%{yellow!}pending%{reset}'))
        if agent.backend is None:
            backend_title = cformat('%{red!}invalid backend ({})%{reset}').format(agent.backend_name)
        else:
            backend_title = agent.backend.title
        table_data.append([str(agent.id), agent.name, backend_title, initial,
                           str(agent.queue.filter_by(processed=False).count())])
    table = AsciiTable(table_data)
    table.justify_columns[4] = 'right'
    print(table.table)
    if not all(a.initial_data_exported for a in agent_list):
        print()
        print("You need to perform the initial data export for some agents.")
        print(cformat("To do so, run "
                      "%{yellow!}indico livesync initial-export %{reset}%{yellow}<agent_id>%{reset} for those agents."))


@cli.command()
@click.argument('agent_id', type=int)
@click.option('--force', is_flag=True, help="Perform export even if it has already been done once.")
def initial_export(agent_id, force):
    """Performs the initial data export for an agent"""
    agent = LiveSyncAgent.get(agent_id)
    if agent is None:
        print('No such agent')
        return
    if agent.backend is None:
        print(cformat('Cannot run agent %{red!}{}%{reset} (backend not found)').format(agent.name))
        return
    print(cformat('Selected agent: %{white!}{}%{reset} ({})').format(agent.name, agent.backend.title))
    if agent.initial_data_exported and not force:
        print('The initial export has already been performed for this agent.')
        print(cformat('To re-run it, use %{yellow!}--force%{reset}'))
        return

    pre_load = Category.query.all()
    Category.allow_relationship_preloading = True
    Category.preload_relationships(Category.query, 'acl_entries')
    backend = agent.create_backend()
    events = query_events()
    contributions = query_contributions()
    attachments = query_attachments()
    notes = query_notes()
    backend.run_initial_export(yield_per(contributions, 5000), contributions.count())
    backend.run_initial_export(yield_per(events, 5000), events.count())
    backend.run_initial_export(yield_per(attachments, 5000), attachments.count())
    backend.run_initial_export(yield_per(notes, 5000), notes.count())
    agent.initial_data_exported = True
    db.session.commit()


def query_events():
    return Event.query.filter_by(is_deleted=False).filter(Event.person_links.any()).options(
        subqueryload(Event.acl_entries),
        joinedload(Event.person_links),
        joinedload('own_venue'),
        joinedload('own_room'),
        undefer('own_address'),
        undefer('detailed_category_chain')
    )


def query_contributions():
    return Contribution.query.filter_by(is_deleted=False).options(
        subqueryload(Contribution.acl_entries),
        joinedload(Contribution.person_links),
        joinedload(Contribution.event).undefer(Event.detailed_category_chain),
        joinedload(Contribution.event).subqueryload(Event.acl_entries),
        joinedload(Contribution.event).joinedload('own_venue'),
        joinedload(Contribution.event).joinedload('own_room'),
        joinedload(Contribution.session).subqueryload(Session.acl_entries),
        joinedload('own_venue'),
        joinedload('own_room'),
        undefer('own_address'),
        subqueryload(Contribution.session_block),
        subqueryload(Contribution.timetable_entry)
    )


def query_attachments():
    contrib_event = db.aliased(Event)
    contrib_session = db.aliased(Session)
    subcontrib_contrib = db.aliased(Contribution)
    subcontrib_session = db.aliased(Session)
    subcontrib_event = db.aliased(Event)
    session_event = db.aliased(Event)

    def _apply_acl_entry_strategy(rel, principal):
        user_strategy = rel.joinedload('user').joinedload('_affiliation')
        user_strategy.noload('*')
        user_strategy.load_only('id')
        rel.joinedload('local_group').load_only('id')
        if principal.allow_networks:
            rel.joinedload('ip_network_group').load_only('id')
        if principal.allow_category_roles:
            rel.joinedload('category_role').load_only('id')
        if principal.allow_event_roles:
            rel.joinedload('event_role').load_only('id')
        if principal.allow_registration_forms:
            rel.joinedload('registration_form').load_only('id')
        return rel

    attachment_strategy = _apply_acl_entry_strategy(selectinload('acl_entries'), AttachmentPrincipal)
    folder_strategy = contains_eager('folder')
    folder_strategy.load_only('id', 'protection_mode', 'link_type', 'category_id', 'event_id', 'linked_event_id',
                              'contribution_id', 'subcontribution_id', 'session_id')
    _apply_acl_entry_strategy(folder_strategy.selectinload('acl_entries'), AttachmentFolderPrincipal)
    # category
    _apply_acl_entry_strategy(folder_strategy.contains_eager('category').selectinload('acl_entries'),
                              CategoryPrincipal)
    # event
    _apply_acl_entry_strategy(folder_strategy.contains_eager('linked_event').selectinload('acl_entries'),
                              EventPrincipal)
    # contribution
    contrib_strategy = folder_strategy.contains_eager('contribution')
    _apply_acl_entry_strategy(contrib_strategy.selectinload('acl_entries'), ContributionPrincipal)
    _apply_acl_entry_strategy(
        contrib_strategy.contains_eager(Contribution.event.of_type(contrib_event)).selectinload('acl_entries'),
        EventPrincipal)
    _apply_acl_entry_strategy(
        contrib_strategy.contains_eager(Contribution.session.of_type(contrib_session)).selectinload('acl_entries'),
        SessionPrincipal)
    # subcontribution
    subcontrib_strategy = folder_strategy.contains_eager('subcontribution')
    subcontrib_contrib_strategy = subcontrib_strategy.contains_eager(
        SubContribution.contribution.of_type(subcontrib_contrib))
    _apply_acl_entry_strategy(subcontrib_contrib_strategy.selectinload('acl_entries'), ContributionPrincipal)
    _apply_acl_entry_strategy(
        subcontrib_contrib_strategy.contains_eager(subcontrib_contrib.event.of_type(subcontrib_event))
        .selectinload('acl_entries'), EventPrincipal)
    _apply_acl_entry_strategy(
        subcontrib_contrib_strategy.contains_eager(subcontrib_contrib.session.of_type(subcontrib_session))
        .selectinload('acl_entries'), SessionPrincipal)
    # session
    session_strategy = folder_strategy.contains_eager('session')
    session_strategy.contains_eager(Session.event.of_type(session_event)).selectinload('acl_entries')
    _apply_acl_entry_strategy(session_strategy.selectinload('acl_entries'), SessionPrincipal)

    return Attachment.query\
        .join(Attachment.folder)\
        .options(folder_strategy, attachment_strategy)\
        .outerjoin(AttachmentFolder.category)\
        .outerjoin(AttachmentFolder.linked_event)\
        .outerjoin(AttachmentFolder.contribution)\
        .outerjoin(Contribution.event.of_type(contrib_event))\
        .outerjoin(Contribution.session.of_type(contrib_session))\
        .outerjoin(AttachmentFolder.subcontribution)\
        .outerjoin(SubContribution.contribution.of_type(subcontrib_contrib))\
        .outerjoin(subcontrib_contrib.event.of_type(subcontrib_event))\
        .outerjoin(subcontrib_contrib.session.of_type(subcontrib_session))\
        .outerjoin(AttachmentFolder.session)\
        .outerjoin(Session.event.of_type(session_event))\
        .filter(~Attachment.is_deleted, ~AttachmentFolder.is_deleted)\
        .filter((AttachmentFolder.link_type != LinkType.category) | (~Category.is_deleted))\
        .filter((AttachmentFolder.link_type != LinkType.event) | (~Event.is_deleted))\
        .filter((AttachmentFolder.link_type != LinkType.contribution) | (
            ~Contribution.is_deleted & ~contrib_event.is_deleted))\
        .filter((AttachmentFolder.link_type != LinkType.subcontribution) | (
            ~SubContribution.is_deleted & ~subcontrib_contrib.is_deleted & ~subcontrib_event.is_deleted))\
        .filter((AttachmentFolder.link_type != LinkType.session) | (~Session.is_deleted & ~session_event.is_deleted))


def query_notes():
    return EventNote.query.filter_by(is_deleted=False).options(
        subqueryload(EventNote.revisions).raiseload(EventNoteRevision.user),
        subqueryload(EventNote.current_revision).raiseload(EventNoteRevision.user),
        selectinload(EventNote.event).undefer(Event.detailed_category_chain),
        selectinload(EventNote.event).subqueryload(Event.acl_entries),
        selectinload(EventNote.contribution).subqueryload(Contribution.acl_entries),
        selectinload(EventNote.contribution).subqueryload(Contribution.session).subqueryload(Session.acl_entries),
        selectinload(EventNote.subcontribution).subqueryload(SubContribution.contribution)
        .subqueryload(Contribution.acl_entries),
        selectinload(EventNote.subcontribution).subqueryload(SubContribution.contribution)
        .subqueryload(Contribution.session).subqueryload(Session.acl_entries),
        selectinload(EventNote.session).subqueryload(Session.acl_entries)
    )


def yield_per(query, window_size=1000):
    index = 0
    while True:
        t1 = time.time()
        chunk = query.slice(index, index + window_size).all()
        t2 = time.time()
        print('Yield took', t2 - t1)
        if not len(chunk):
            break
        for e in chunk:
            yield e
        index += window_size


@cli.command()
@click.argument('agent_id', type=int, required=False)
@click.option('--force', is_flag=True, help="Run even if initial export was not done")
def run(agent_id, force=False):
    """Runs the livesync agent"""
    if agent_id is None:
        agent_list = LiveSyncAgent.query.all()
    else:
        agent = LiveSyncAgent.get(agent_id)
        if agent is None:
            print('No such agent')
            return
        agent_list = [agent]

    for agent in agent_list:
        if agent.backend is None:
            print(cformat('Skipping agent: %{red!}{}%{reset} (backend not found)').format(agent.name))
            continue
        if not agent.initial_data_exported and not force:
            print(cformat('Skipping agent: %{red!}{}%{reset} (initial export not performed)').format(agent.name))
            continue
        print(cformat('Running agent: %{white!}{}%{reset}').format(agent.name))
        try:
            agent.create_backend().run()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
