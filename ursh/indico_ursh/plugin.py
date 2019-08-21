# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask_pluginengine import render_plugin_template
from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired

from indico.core.plugins import IndicoPlugin
from indico.web.forms.base import IndicoForm
from indico.web.views import WPBase

from indico_ursh import _
from indico_ursh.blueprint import blueprint
from indico_ursh.util import is_configured


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
        if is_configured() and (target or event):
            return render_plugin_template('ursh_link.html', target=target, event=event,
                                          dropdown=dropdown, element_class=element_class, text=text, **kwargs)

    def _inject_ursh_footer(self, **kwargs):
        if is_configured():
            return render_plugin_template('ursh_footer.html')
