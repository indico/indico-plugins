# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from sqlalchemy.orm.attributes import flag_modified
from wtforms.fields.core import BooleanField

from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from indico.modules.vc import VCPluginMixin
from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.web.forms.widgets import SwitchWidget


class VCRoomForm(VCRoomFormBase):
    show_phone_numbers = BooleanField('What is your favorite color?',
                                      widget=SwitchWidget(),
                                      description="Yes. It doesn't make any sense.")


class VCRoomAttachForm(VCRoomAttachFormBase):
    show_phone_numbers = BooleanField('What is your favorite color?',
                                      widget=SwitchWidget(),
                                      description="Yes. It doesn't make any sense.")


class DummyPlugin(VCPluginMixin, IndicoPlugin):
    """Dummy

    Dummy videoconferencing plugin
    """
    configurable = True
    vc_room_form = VCRoomForm
    vc_room_attach_form = VCRoomAttachForm
    friendly_name = "Dummy"

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/dummy_logo.png')

    @property
    def icon_url(self):
        return url_for_plugin(self.name + '.static', filename='images/dummy_icon.png')

    def get_blueprints(self):
        return IndicoPluginBlueprint('vc_dummy', __name__)

    def create_room(self, vc_room, event):
        pass

    def delete_room(self, vc_room, event):
        pass

    def update_room(self, vc_room, event):
        pass

    def refresh_room(self, vc_room, event):
        pass

    def update_data_association(self, event, vc_room, event_vc_room, data):
        super(DummyPlugin, self).update_data_association(event, vc_room, event_vc_room, data)
        event_vc_room.data.update({key: data.pop(key) for key in [
            'show_phone_numbers'
        ]})

        flag_modified(event_vc_room, 'data')
