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

from flask import session
from sqlalchemy.orm.attributes import flag_modified
from wtforms.fields import IntegerField, TextAreaField
from wtforms.fields.html5 import EmailField, URLField
from wtforms.fields.simple import StringField
from wtforms.validators import DataRequired, NumberRange

from indico.core import signals
from indico.core.auth import multipass
from indico.core.config import config
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.views import WPSimpleEventDisplay
from indico.modules.vc import VCPluginMixin, VCPluginSettingsFormBase
from indico.modules.vc.exceptions import VCRoomError, VCRoomNotFoundError
from indico.modules.vc.views import WPVCEventPage, WPVCManageEvent
from indico.web.forms.fields import IndicoPasswordField
from indico.web.forms.widgets import CKEditorWidget
from indico.web.http_api.hooks.base import HTTPAPIHook

from indico_vc_vidyo import _
from indico_vc_vidyo.api import AdminClient, APIException, RoomNotFoundAPIException
from indico_vc_vidyo.blueprint import blueprint
from indico_vc_vidyo.cli import cli
from indico_vc_vidyo.forms import VCRoomAttachForm, VCRoomForm
from indico_vc_vidyo.http_api import DeleteVCRoomAPI
from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension
from indico_vc_vidyo.util import iter_extensions, iter_user_identities, retrieve_principal, update_room_from_obj


class PluginSettingsForm(VCPluginSettingsFormBase):
    support_email = EmailField(_('Vidyo email support'))
    username = StringField(_('Username'), [DataRequired()], description=_('Indico username for Vidyo'))
    password = IndicoPasswordField(_('Password'), [DataRequired()], toggle=True,
                                   description=_('Indico password for Vidyo'))
    admin_api_wsdl = URLField(_('Admin API WSDL URL'), [DataRequired()])
    user_api_wsdl = URLField(_('User API WSDL URL'), [DataRequired()])
    indico_room_prefix = IntegerField(_('Indico tenant prefix'), [NumberRange(min=0)],
                                      description=_('The tenant prefix for Indico rooms created on this server'))
    room_group_name = StringField(_("Public rooms' group name"), [DataRequired()],
                                  description=_('Group name for public videoconference rooms created by Indico'))
    authenticators = StringField(_('Authenticators'), [DataRequired()],
                                 description=_('Identity providers to convert Indico users to Vidyo accounts'))
    num_days_old = IntegerField(_('VC room age threshold'), [NumberRange(min=1), DataRequired()],
                                description=_('Number of days after an Indico event when a videoconference room is '
                                              'considered old'))
    max_rooms_warning = IntegerField(_('Max. num. VC rooms before warning'), [NumberRange(min=1), DataRequired()],
                                     description=_('Maximum number of rooms until a warning is sent to the managers'))
    vidyo_phone_link = URLField(_('VidyoVoice phone number'),
                                description=_('Link to the list of VidyoVoice phone numbers'))
    client_chooser_url = URLField(_('Client Chooser URL'),
                                  description=_("URL for client chooser interface. The room key will be passed as a "
                                                "'url' GET query argument"))
    creation_email_footer = TextAreaField(_('Creation email footer'), widget=CKEditorWidget(),
                                          description=_('Footer to append to emails sent upon creation of a VC room'))


class VidyoPlugin(VCPluginMixin, IndicoPlugin):
    """Vidyo

    Videoconferencing with Vidyo
    """
    configurable = True
    settings_form = PluginSettingsForm
    vc_room_form = VCRoomForm
    vc_room_attach_form = VCRoomAttachForm
    friendly_name = 'Vidyo'

    def init(self):
        super(VidyoPlugin, self).init()
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.inject_js('vc_vidyo_js', WPSimpleEventDisplay)
        self.inject_js('vc_vidyo_js', WPVCEventPage)
        self.inject_js('vc_vidyo_js', WPVCManageEvent)
        HTTPAPIHook.register(DeleteVCRoomAPI)

    @property
    def default_settings(self):
        return dict(VCPluginMixin.default_settings, **{
            'support_email': config.SUPPORT_EMAIL,
            'username': 'indico',
            'password': None,
            'admin_api_wsdl': 'https://yourvidyoportal/services/v1_1/VidyoPortalAdminService?wsdl',
            'user_api_wsdl': 'https://yourvidyoportal/services/v1_1/VidyoPortalUserService?wsdl',
            'indico_room_prefix': 10,
            'room_group_name': 'Indico',
            # we skip identity providers in the default list if they don't support get_identity.
            # these providers (local accounts, oauth) are unlikely be the correct ones to integrate
            # with the vidyo infrastructure.
            'authenticators': ', '.join(p.name for p in multipass.identity_providers.itervalues() if p.supports_get),
            'num_days_old': 365,
            'max_rooms_warning': 5000,
            'vidyo_phone_link': None,
            'creation_email_footer': None,
            'client_chooser_url': None
        })

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    @property
    def icon_url(self):
        return url_for_plugin(self.name + '.static', filename='images/vidyo_logo_notext.png')

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def update_data_association(self, event, vc_room, event_vc_room, data):
        super(VidyoPlugin, self).update_data_association(event, vc_room, event_vc_room, data)

        event_vc_room.data.update({key: data.pop(key) for key in [
            'show_pin',
            'show_autojoin',
            'show_phone_numbers'
        ]})

        flag_modified(event_vc_room, 'data')

    def update_data_vc_room(self, vc_room, data):
        super(VidyoPlugin, self).update_data_vc_room(vc_room, data)

        for key in ['description', 'owner', 'room_pin', 'moderation_pin', 'auto_mute']:
            if key in data:
                vc_room.data[key] = data.pop(key)

        flag_modified(vc_room, 'data')

    def create_room(self, vc_room, event):
        """Create a new Vidyo room for an event, given a VC room.

        In order to create the Vidyo room, the function will try to do so with
        all the available identities of the user based on the authenticators
        defined in Vidyo plugin's settings, in that order.

        :param vc_room: VCRoom -- The VC room from which to create the Vidyo
                        room
        :param event: Event -- The event to the Vidyo room will be attached
        """
        client = AdminClient(self.settings)
        owner = retrieve_principal(vc_room.data['owner'])
        login_gen = iter_user_identities(owner)
        login = next(login_gen, None)
        if login is None:
            raise VCRoomError(_("No valid Vidyo account found for this user"), field='owner_user')

        extension_gen = iter_extensions(self.settings.get('indico_room_prefix'), event.id)
        extension = next(extension_gen)

        while True:
            room_mode = {
                'isLocked': False,
                'hasPIN': bool(vc_room.data['room_pin']),
                'hasModeratorPIN': bool(vc_room.data['moderation_pin'])
            }
            if room_mode['hasPIN']:
                room_mode['roomPIN'] = vc_room.data['room_pin']
            if room_mode['hasModeratorPIN']:
                room_mode['moderatorPIN'] = vc_room.data['moderation_pin']

            room_obj = client.create_room_object(
                name=vc_room.name,
                RoomType='Public',
                ownerName=login,
                extension=extension,
                groupName=self.settings.get('room_group_name'),
                description=vc_room.data['description'],
                RoomMode=room_mode)

            if room_obj.RoomMode.hasPIN:
                room_obj.RoomMode.roomPIN = vc_room.data['room_pin']
            if room_obj.RoomMode.hasModeratorPIN:
                room_obj.RoomMode.moderatorPIN = vc_room.data['moderation_pin']

            try:
                client.add_room(room_obj)
            except APIException as err:
                err_msg = err.message

                if err_msg.startswith('Room exist for name'):
                    raise VCRoomError(_("Room name already in use"), field='name')
                elif err_msg.startswith('Member not found for ownerName'):
                    login = next(login_gen, None)
                    if login is None:
                        raise VCRoomError(_("No valid Vidyo account found for this user"), field='owner_user')
                elif err_msg.startswith('Room exist for extension'):
                    extension = next(extension_gen)
                else:
                    raise

            else:
                # get room back, in order to fetch Vidyo-set parameters
                created_room = client.find_room(extension)

                if not created_room:
                    raise VCRoomNotFoundError(_("Could not find newly created room in Vidyo"))
                vc_room.data.update({
                    'vidyo_id': unicode(created_room.roomID),
                    'url': created_room.RoomMode.roomURL,
                    'owner_identity': created_room.ownerName
                })
                flag_modified(vc_room, 'data')
                vc_room.vidyo_extension = VidyoExtension(vc_room_id=vc_room.id, extension=int(created_room.extension),
                                                         owned_by_user=owner)

                client.set_automute(created_room.roomID, vc_room.data['auto_mute'])
                break

    def update_room(self, vc_room, event):
        client = AdminClient(self.settings)

        try:
            room_obj = self.get_room(vc_room)
        except RoomNotFoundAPIException:
            raise VCRoomNotFoundError(_("This room has been deleted from Vidyo"))

        owner = retrieve_principal(vc_room.data['owner'])
        changed_owner = room_obj.ownerName not in iter_user_identities(owner)
        if changed_owner:
            login_gen = iter_user_identities(owner)
            login = next(login_gen, None)
            if login is None:
                raise VCRoomError(_("No valid Vidyo account found for this user"), field='owner_user')
            room_obj.ownerName = login

        room_obj.name = vc_room.name
        room_obj.description = vc_room.data['description']

        room_obj.RoomMode.hasPIN = bool(vc_room.data['room_pin'])
        room_obj.RoomMode.hasModeratorPIN = bool(vc_room.data['moderation_pin'])

        if room_obj.RoomMode.hasPIN:
            room_obj.RoomMode.roomPIN = vc_room.data['room_pin']
        if room_obj.RoomMode.hasModeratorPIN:
            room_obj.RoomMode.moderatorPIN = vc_room.data['moderation_pin']

        vidyo_id = vc_room.data['vidyo_id']
        while True:
            try:
                client.update_room(vidyo_id, room_obj)
            except RoomNotFoundAPIException:
                raise VCRoomNotFoundError(_("This room has been deleted from Vidyo"))
            except APIException as err:
                err_msg = err.message
                if err_msg.startswith('Room exist for name'):
                    raise VCRoomError(_("Room name already in use"), field='name')

                elif err_msg.startswith('Member not found for ownerName'):
                    if changed_owner:
                        login = next(login_gen, None)
                    if not changed_owner or login is None:
                        raise VCRoomError(_("No valid Vidyo account found for this user"), field='owner_user')
                    room_obj.ownerName = login

                else:
                    raise
            else:
                updated_room_obj = self.get_room(vc_room)

                update_room_from_obj(self.settings, vc_room, updated_room_obj)
                flag_modified(vc_room, 'data')

                client.set_automute(vidyo_id, vc_room.data['auto_mute'])
                break

    def refresh_room(self, vc_room, event):
        client = AdminClient(self.settings)
        try:
            room_obj = self.get_room(vc_room)
        except RoomNotFoundAPIException:
            raise VCRoomNotFoundError(_("This room has been deleted from Vidyo"))

        update_room_from_obj(self.settings, vc_room, room_obj)
        vc_room.data['auto_mute'] = client.get_automute(room_obj.roomID)
        flag_modified(vc_room, 'data')

    def delete_room(self, vc_room, event):
        client = AdminClient(self.settings)

        vidyo_id = vc_room.data['vidyo_id']
        try:
            client.delete_room(vidyo_id)
        except RoomNotFoundAPIException:
            pass

    def get_room(self, vc_room):
        client = AdminClient(self.settings)
        return client.get_room(vc_room.data['vidyo_id'])

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_js_bundle('vc_vidyo_js', 'js/vc_vidyo.js')

    def get_vc_room_form_defaults(self, event):
        defaults = super(VidyoPlugin, self).get_vc_room_form_defaults(event)
        defaults.update({
            'auto_mute': True,
            'show_pin': False,
            'show_autojoin': True,
            'show_phone_numbers': True,
            'owner_user': session.user
        })

        return defaults

    def get_vc_room_attach_form_defaults(self, event):
        defaults = super(VidyoPlugin, self).get_vc_room_attach_form_defaults(event)
        defaults.update({
            'show_pin': False,
            'show_autojoin': True,
            'show_phone_numbers': True
        })
        return defaults

    def can_manage_vc_room(self, user, room):
        return user == room.vidyo_extension.owned_by_user or super(VidyoPlugin, self).can_manage_vc_room(user, room)

    def _merge_users(self, target, source, **kwargs):
        super(VidyoPlugin, self)._merge_users(target, source, **kwargs)
        for ext in VidyoExtension.find(owned_by_user=source):
            ext.owned_by_user = target
            flag_modified(ext.vc_room, 'data')

    def get_notification_cc_list(self, action, vc_room, event):
        return {vc_room.vidyo_extension.owned_by_user.email}
