# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import flash, redirect, request
from flask_pluginengine import current_plugin, render_plugin_template
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.exceptions import NotFound

from indico.core.db import db
from indico.core.errors import UserValueError
from indico.modules.admin import RHAdminBase
from indico.web.flask.util import url_for
from indico.web.forms.base import FormDefaults
from indico.web.util import jsonify_data, jsonify_template

from indico_livesync import _
from indico_livesync.models.agents import LiveSyncAgent


def extend_plugin_details():
    agents = LiveSyncAgent.query.order_by(LiveSyncAgent.name, LiveSyncAgent.id).all()
    used_backends = {a.backend_name for a in agents}
    available_backends = {name: backend
                          for name, backend in current_plugin.backend_classes.items()
                          if not backend.unique or name not in used_backends}
    return render_plugin_template('plugin_details_extra.html', agents=agents, backends=available_backends)


class RHDeleteAgent(RHAdminBase):
    """Deletes a LiveSync agent"""

    def _process_args(self):
        self.agent = LiveSyncAgent.get_or_404(request.view_args['agent_id'])

    def _process(self):
        db.session.delete(self.agent)
        flash(_('Agent deleted'), 'success')
        return jsonify_data(flash=False)


class RHAddAgent(RHAdminBase):
    """Adds a LiveSync agent"""

    def _process_args(self):
        self.backend_name = request.view_args['backend']
        try:
            self.backend = current_plugin.backend_classes[self.backend_name]
        except KeyError:
            raise NotFound
        if self.backend.unique and LiveSyncAgent.query.filter_by(backend_name=self.backend_name).has_rows():
            raise UserValueError(_('This backend is already in use'))

    def _process(self):
        form = self.backend.form(obj=FormDefaults(name=self.backend.title))
        if form.validate_on_submit():
            data = form.data
            name = data.pop('name')
            agent = LiveSyncAgent(name=name, backend_name=self.backend_name, settings=data)
            db.session.add(agent)
            flash(_('Agent added'), 'success')
            flash(_("Don't forget to run the initial export!"), 'highlight')
            return jsonify_data(flash=False)

        return jsonify_template('edit_agent.html', render_plugin_template, form=form, backend=self.backend, edit=False)


class RHEditAgent(RHAdminBase):
    """Edits a LiveSync agent"""

    def _process_args(self):
        self.agent = LiveSyncAgent.get_or_404(request.view_args['agent_id'])
        if self.agent.backend is None:
            flash(_('Cannot edit an agent that is not loaded'), 'error')
            return redirect(url_for('plugins.details', plugin='livesync'))

    def _process(self):
        form = self.agent.backend.form(obj=FormDefaults(name=self.agent.name, **self.agent.settings))
        if form.validate_on_submit():
            data = form.data
            self.agent.name = data.pop('name')
            if data:
                self.agent.settings.update(data)
                flag_modified(self.agent, 'settings')
            flash(_('Agent updated'), 'success')
            return jsonify_data(flash=False)

        return jsonify_template('edit_agent.html', render_plugin_template, form=form, backend=self.agent.backend,
                                edit=True)
