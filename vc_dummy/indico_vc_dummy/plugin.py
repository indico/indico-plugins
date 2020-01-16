# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
