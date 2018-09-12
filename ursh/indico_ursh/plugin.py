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

from flask_pluginengine import render_plugin_template

from indico.core.plugins import IndicoPlugin
from indico.web.flask.util import url_for
from indico.web.forms.base import IndicoForm
from indico.web.views import WPBase

from indico_ursh import _
from indico_ursh.blueprint import blueprint
from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired


class SettingsForm(IndicoForm):
    api_key = StringField(_('API key'), [DataRequired()],
                          description=_('The API key to access the <tt>ursh</tt> service'))
    api_host = URLField(_('API host'), [DataRequired()],
                        description=_('The <tt>ursh</tt> API host, providing the interface to generate short URLs'))


class UrshPlugin(IndicoPlugin):
    """URL Shortener

    Provides a URL shortening service for indico assets, events, etc.
    """

    configurable = True
    settings_form = SettingsForm
    default_settings = {
        'api_key': '',
        'api_host': '',
    }

    def init(self):
        super(UrshPlugin, self).init()
        self.template_hook('url-shortener', self._inject_ursh_link)
        self.template_hook('page-footer', self._inject_ursh_footer)
        self.inject_bundle('main.js', WPBase)

    def get_blueprints(self):
        return blueprint

    def _inject_ursh_link(self, target=None, event=None, dropdown=False, element_class='', text='', **kwargs):
        if self.settings.get('api_key') and self.settings.get('api_host') and (target or event):
            return render_plugin_template('ursh_link.html', target=target, event=event,
                                          dropdown=dropdown, element_class=element_class, text=text, **kwargs)

    def _inject_ursh_footer(self, **kwargs):
        url = url_for('plugin_ursh.shorten_url')
        return render_plugin_template('ursh_footer.html')
