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
import re

from sqlalchemy.orm.attributes import flag_modified
from suds import WebFault
from wtforms.fields import IntegerField, TextAreaField
from wtforms.fields.html5 import URLField, EmailField
from wtforms.fields.simple import StringField
from wtforms.validators import NumberRange, DataRequired

from indico.core.config import Config
from indico.core.plugins import IndicoPlugin, url_for_plugin, IndicoPluginBlueprint
from indico.modules.vc import VCPluginSettingsFormBase, VCPluginMixin
from indico.modules.vc.views import WPVCManageEvent
from indico.util.i18n import _
from indico.util.user import retrieve_principal
from indico.web.forms.fields import EmailListField, IndicoPasswordField
from indico.web.forms.widgets import CKEditorWidget

from indico_vc_vidyo.api import AdminClient
from indico_vc_vidyo.forms import VCRoomForm
from indico_vc_vidyo.util import iter_user_identities
from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension


class PluginSettingsForm(VCPluginSettingsFormBase):
    support_email = EmailField(_('Vidyo email support'))
    notification_emails = EmailListField(
        _('Notification emails'),
        description=_('Additional email addresses who will always receive notifications (one per line)')
    )
    username = StringField(_('Username'), [DataRequired()], description=_('Indico username for Vidyo'))
    password = IndicoPasswordField(_('Password'), [DataRequired()], toggle=True,
                                   description=_('Indico password for Vidyo'))
    admin_api_wsdl = URLField(_('Admin API WSDL URL'), [DataRequired()])
    user_api_wsdl = URLField(_('User API WSDL URL'), [DataRequired()])
    indico_room_prefix = IntegerField(_('Indico rooms prefix'), [NumberRange(min=0)],
                                      description=_('The prefix for Indico rooms'))
    room_group_name = StringField(_("Public rooms' group name"), [DataRequired()],
                                  description=_('Group name for public video conference rooms created by Indico'))
    authenticators = StringField(_('Authenticators'), [DataRequired()],
                                 description=_('Authenticators to convert Indico users to Vidyo accounts'))
    num_days_old = IntegerField(_('VC room age threshold'), [NumberRange(min=1), DataRequired()],
                                description=_('Number of days after an Indico event when a video conference room is '
                                              'considered old'))
    max_rooms_warning = IntegerField(_('Max. num. VC rooms before warning'), [NumberRange(min=1), DataRequired()],
                                     description=_('Maximum number of rooms until a warning is sent to the managers'))
    vidyo_phone_link = URLField(_('VidyoVoice phone number'),
                                description=_('Link to the list of VidyoVoice phone numbers'))
    creation_email_footer = TextAreaField(_('Creation email footer'), widget=CKEditorWidget(),
                                          description=_('Footer to append to emails sent upon creation of a VC room'))


class VidyoPlugin(VCPluginMixin, IndicoPlugin):
    """Vidyo

    Video conferencing with Vidyo
    """
    configurable = True
    strict_settings = True
    settings_form = PluginSettingsForm
    default_settings = {
        'managers': [],
        'acl': [],
        'notify_managers': True,
        'support_email': Config.getInstance().getSupportEmail(),
        'notification_emails': [],
        'username': 'indico',
        'password': None,
        'admin_api_wsdl': 'https://yourvidyoportal/services/v1_1/VidyoPortalAdminService?wsdl',
        'user_api_wsdl': 'https://yourvidyoportal/services/v1_1/VidyoPortalUserService?wsdl',
        'indico_room_prefix': 10,
        'room_group_name': 'Indico',
        'authenticators': ', '.join(auth[0] for auth in Config.getInstance().getAuthenticatorList()),
        'num_days_old': 180,
        'max_rooms_warning': 5000,
        'vidyo_phone_link': None,
        'creation_email_footer': None

    }
    vc_room_form = VCRoomForm

    def init(self):
        super(VidyoPlugin, self).init()
        self.inject_css('vc_vidyo_css', WPVCManageEvent)

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def create_room(self, vc_room, event):
        client = AdminClient(self.settings)

        room_moderator = retrieve_principal(vc_room.data['moderator'])

        for login in iter_user_identities(room_moderator):

            extension = "{}{}".format(self.settings.get('indico_room_prefix'), event.id)

            room_obj = client.create_room_object(
                name=vc_room.name,
                RoomType='Public',
                ownerName=login,
                extension=extension,
                groupName=self.settings.get('room_group_name'),
                description=vc_room.data['description'])

            room_obj.RoomMode.isLocked = False
            room_obj.RoomMode.hasPIN = vc_room.data['room_pin'] != ""
            room_obj.RoomMode.hasModeratorPIN = vc_room.data['moderator_pin'] != ""

            if room_obj.RoomMode.hasPIN:
                room_obj.RoomMode.roomPIN = vc_room.data['room_pin']
            if room_obj.RoomMode.hasModeratorPIN:
                room_obj.RoomMode.moderatorPIN = vc_room.data['moderator_pin']

            try:
                client.add_room(room_obj)
            except WebFault as err:
                self.logger.exception('Problem creating the room')
                pass
                # err_msg = err.fault.faultstring
                # if err_msg.startswith
                # if faultString.startswith('Room exist for name'):
                #     if VidyoOperations.roomWithSameOwner(possibleLogins[loginToUse], roomNameForVidyo):
                #         return VidyoError("duplicatedWithOwner", "create")
                #     else:
                #         return VidyoError("duplicated", "create")

                # elif faultString.startswith('Member not found for ownerName'):
                #     loginToUse = loginToUse + 1

                # elif faultString.startswith('PIN should be a 3-10 digit number'):
                #         return VidyoError("PINLength", "create")

                # elif faultString.startswith('Room exist for extension'):


            # get room back, in order to fetch Vidyo-set parameters
            created_room = client.find_room(extension)[0]

            vc_room.data.update({
                'vidyo_id': unicode(created_room.roomID),
                'url': created_room.RoomMode.roomURL,
                'owner_identity': created_room.ownerName
            })
            vc_room.vidyo_extension = VidyoExtension(vc_room_id=vc_room.id, value=int(created_room.extension))
            flag_modified(vc_room, 'data')

            client.set_automute(created_room.roomID, vc_room.data['auto_mute'])
            break

    def update_room(self, vc_room, event):
        client = AdminClient(self.settings)
        vidyo_id = vc_room.data['vidyo_id']
        try:
            room_obj = self.get_room(vc_room)
        except WebFault as err:
            self.logger.exception("Unable to retrieve room with id {room.data[vidyo_id]}".format(room=room_obj))
            # TODO: handle errors
            pass

        room_obj.name = vc_room.name
        return client.update_room(vidyo_id, room_obj)

    def get_room(self, vc_room):
        client = AdminClient(self.settings)
        return client.get_room(vc_room.data['vidyo_id'])

    def register_assets(self):
        self.register_css_bundle('vc_vidyo_css', 'css/vc_vidyo.scss')

    def get_blueprints(self):
        return IndicoPluginBlueprint('vc_vidyo', __name__)

    def get_vc_room_form_defaults(self, event):
        return {
            # replace invalid chars with underscore
            'name': re.sub(r'[^\w_-]', '_', event.getTitle()),
            'linking': 'event',
            'contribution': '',
            'session': '',
            'auto_mute': True,
            'show_pin': False,
            'show_autojoin': True,
            'show_phone_numbers': True,
            'show': True
        }
