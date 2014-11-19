# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from flask import request, redirect, flash
from flask_pluginengine import render_plugin_template, current_plugin

from indico.core.db import db
from indico.util.i18n import _
from indico.web.flask.util import url_for
from indico.web.forms.base import FormDefaults
from MaKaC.webinterface.rh.admins import RHAdminBase

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.views import WPLiveSync


def extend_plugin_details():
    agents = LiveSyncAgent.find().order_by(LiveSyncAgent.name, LiveSyncAgent.id).all()
    return render_plugin_template('plugin_details_extra.html', agents=agents, backends=current_plugin.agent_classes)


class RHDeleteAgent(RHAdminBase):
    """Deletes a LiveSync agent"""

    def _checkParams(self):
        self.agent = LiveSyncAgent.find_one(id=request.view_args['agent_id'])

    def _process(self):
        db.session.delete(self.agent)
        flash(_('Agent deleted'), 'success')
        return redirect(url_for('plugins.details', plugin='livesync'))


class RHAddAgent(RHAdminBase):
    """Adds a LiveSync agent"""

    def _checkParams(self):
        self.backend_name = request.view_args['backend']
        self.backend = current_plugin.agent_classes[self.backend_name]

    def _process(self):
        form = self.backend.form(obj=FormDefaults(name=self.backend.title))
        if form.validate_on_submit():
            data = form.data
            name = data.pop('name')
            agent = LiveSyncAgent(name=name, backend_name=self.backend_name, settings=data)
            db.session.add(agent)
            flash(_('Agent added'), 'success')
            flash(_("Don't forget to run the initial export!"), 'highlight')
            return redirect(url_for('plugins.details', plugin='livesync'))

        return WPLiveSync.render_template('edit_agent.html', form=form, backend=self.backend)


class RHEditAgent(RHAdminBase):
    """Edits a LiveSync agent"""

    def _checkParams(self):
        self.agent = LiveSyncAgent.find_one(id=request.view_args['agent_id'])
        if self.agent.backend is None:
            flash(_('Cannot edit an agent that is not loaded'), 'error')
            return redirect(url_for('plugins.details', plugin='livesync'))

    def _process(self):
        form = self.agent.backend.form(obj=FormDefaults(self.agent, {'name'}, **self.agent.settings))
        if form.validate_on_submit():
            data = form.data
            self.agent.name = data.pop('name')
            self.agent.settings = data
            flash(_('Agent updated'), 'success')
            return redirect(url_for('plugins.details', plugin='livesync'))

        return WPLiveSync.render_template('edit_agent.html', form=form, backend=self.agent.backend, agent=self.agent)
