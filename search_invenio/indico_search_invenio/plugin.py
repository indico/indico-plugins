# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
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

from wtforms.fields.core import SelectField
from wtforms.fields.html5 import IntegerField, URLField
from wtforms.validators import URL, NumberRange

from indico.core.plugins import IndicoPluginBlueprint
from indico.web.forms.base import IndicoForm

from indico_search import SearchPluginBase
from indico_search.views import WPSearchCategory, WPSearchConference
from indico_search_invenio import _
from indico_search_invenio.engine import InvenioSearchEngine
from indico_search_invenio.forms import InvenioSearchForm


class SettingsForm(IndicoForm):
    search_url = URLField(_('Invenio URL'), [URL()])
    display_mode = SelectField(_('Display mode'), choices=[('api_public', _('Embedded (public data)')),
                                                           ('api_private', _('Embedded (private data)')),
                                                           ('redirect', _('External (Redirect)'))])
    results_per_page = IntegerField(_('Results per page'), [NumberRange(min=5)],
                                    description=_("Number of results to show per page (only in embedded mode)"))


class InvenioSearchPlugin(SearchPluginBase):
    """Invenio Search

    Uses Invenio as Indico's search engine
    """
    configurable = True
    settings_form = SettingsForm
    default_settings = {
        'search_url': None,
        'display_mode': 'redirect',
        'results_per_page': 20
    }
    engine_class = InvenioSearchEngine
    search_form = InvenioSearchForm

    def init(self):
        super(InvenioSearchPlugin, self).init()
        for wp in (WPSearchCategory, WPSearchConference):
            self.inject_css('search_invenio_css', wp)
            self.inject_js('search_invenio_js', wp)

    def register_assets(self):
        self.register_css_bundle('search_invenio_css', 'css/search_invenio.scss')
        self.register_js_bundle('search_invenio_js', 'js/search_invenio.js')

    def get_blueprints(self):
        return IndicoPluginBlueprint('search_invenio', 'indico_search_invenio')
