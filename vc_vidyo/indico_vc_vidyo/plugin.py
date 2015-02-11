# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from wtforms.fields.html5 import URLField, EmailField
from wtforms.fields.simple import StringField

from indico.core.plugins import IndicoPlugin, url_for_plugin, IndicoPluginBlueprint
from indico.modules.vc import VCPluginSettingsFormBase, VCPluginMixin
from indico.util.i18n import _
from indico.web.forms.fields import MultipleItemsField, EmailListField, UnsafePasswordField
from indico_vc_vidyo.forms import VCRoomForm


class PluginSettingsForm(VCPluginSettingsFormBase):
    event_types = MultipleItemsField(_('Supported event types'), fields=(('type', 'Type'),),
                                     description=_("Kind of event types (conference, meeting, simple_event) supported"))
    vidyo_support = EmailField(_('Vidyo email support'))
    notify_emails = EmailListField(_('Notification emails'),
                                   description=_('Additional email addresses who will always receive notifications'
                                                 '(one per line)'))
    username = StringField(_('Username'), description=_('Indico username for Vidyo'))
    password = UnsafePasswordField(_('Password'), description=_('Indico password for Vidyo'))
    api_base_url = URLField(_('Vidyo API base URL'))
    api_wsdl_url = URLField(_('Admin API WSDL URL'))
    user_api = StringField(_('User API Service'))


class VidyoPlugin(VCPluginMixin, IndicoPlugin):
    """Vidyo

    Video conferencing with Vidyo
    """
    configurable = True
    settings_form = PluginSettingsForm
    vc_room_form = VCRoomForm

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return IndicoPluginBlueprint('vc_vidyo', __name__)
