# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template
from wtforms.fields import StringField, URLField
from wtforms.validators import DataRequired

from indico.core.plugins import IndicoPlugin
from indico.modules.attachments.views import WPEventAttachments
from indico.modules.categories.views import WPCategoryManagement
from indico.modules.events.views import WPConferenceDisplay, WPSimpleEventDisplay
from indico.web.forms.base import IndicoForm

from indico_owncloud import _
from indico_owncloud.blueprint import blueprint
from indico_owncloud.util import is_configured


class PluginSettingsForm(IndicoForm):
    filepicker_url = URLField(_('File-picker URL'), [DataRequired()])
    service_name = StringField(_('Service name'), [],
                               description=_('A customized name for the cloud service. If empty, the default '
                                             "'The cloud' will be used."))
    button_icon_url = URLField(_('Custom icon URL'), [],
                               description=_('URL for a customized icon to show in the add attachment button. If '
                                             'empty, the default cloud icon will be used'))


class OwncloudPlugin(IndicoPlugin):
    """OwnCloud integration

    Provides an integration with OwnCloud storage servers, enabling managers
    to attach files to categories/events from their cloud storage.
    """
    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'filepicker_url': '',
        'service_name': '',
        'button_icon_url': '',
    }

    def init(self):
        super().init()
        self.template_hook('attachment-sources', self._inject_owncloud_button)
        self.inject_bundle('owncloud.js', WPEventAttachments)
        self.inject_bundle('owncloud.js', WPSimpleEventDisplay)
        self.inject_bundle('owncloud.js', WPConferenceDisplay)
        self.inject_bundle('owncloud.js', WPCategoryManagement)
        self.inject_bundle('main.css', WPEventAttachments)
        self.inject_bundle('main.css', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPConferenceDisplay)
        self.inject_bundle('main.css', WPCategoryManagement)

    def get_blueprints(self):
        return blueprint

    def _inject_owncloud_button(self, linked_object=None, **kwargs):
        if is_configured():
            return render_plugin_template('owncloud_button.html', id=linked_object.id, linked_object=linked_object,
                                          service_name=self.settings.get('service_name'),
                                          button_icon_url=self.settings.get('button_icon_url'))
