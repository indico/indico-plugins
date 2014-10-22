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

from flask import request, session
from flask_pluginengine import current_plugin

from MaKaC.conference import ConferenceHolder, Conference, CategoryManager
from MaKaC.webinterface.rh.conferenceBase import RHCustomizable
from indico_search.views import WPSearchCategory, WPSearchEvent


class RHSearch(RHCustomizable):
    def _checkParams(self):
        if 'confId' in request.view_args:
            self.obj = ConferenceHolder().getById(request.view_args['confId'])
            self.obj_type = 'event'
        elif 'categId' in request.view_args:
            self.obj = CategoryManager().getById(request.view_args['categId'])
            self.obj_type = 'category' if not self.obj.isRoot() else None
        else:
            self.obj = CategoryManager().getRoot()
            self.obj_type = None

        try:
            self.page = int(request.values['page'])
        except (ValueError, KeyError):
            self.page = 1

    def _process(self):
        with current_plugin.engine_plugin.plugin_context():
            form = current_plugin.search_form()
            view_class = WPSearchEvent if isinstance(self.obj, Conference) else WPSearchCategory
            result = None
            if form.validate_on_submit():
                result = current_plugin.perform_search(form.data, self.obj, self.page)
            return view_class.render_template('results.html', self.obj, only_public=current_plugin.only_public,
                                              form=form, obj_type=self.obj_type, result=result)
