# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
            self.inject_bundle('main.js', wp)
            self.inject_bundle('main.css', wp)

    def get_blueprints(self):
        return IndicoPluginBlueprint('search_invenio', 'indico_search_invenio')
