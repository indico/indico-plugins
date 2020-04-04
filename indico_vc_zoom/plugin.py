

from __future__ import unicode_literals

from flask import session
from flask_pluginengine import current_plugin
from sqlalchemy.orm.attributes import flag_modified
from wtforms.fields.core import BooleanField
from wtforms.fields import IntegerField, TextAreaField
from wtforms.fields.html5 import EmailField, URLField
from wtforms.fields.simple import StringField, BooleanField

from indico.web.forms.widgets import SwitchWidget

from indico.web.flask.templating import get_template_module
from wtforms.validators import DataRequired, NumberRange
from indico.core.notifications import make_email, send_email
from indico.core.plugins import get_plugin_template_module
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
from indico.modules.vc.notifications import _send

from indico_vc_zoom import _
from indico_vc_zoom.api import ZoomIndicoClient, APIException, RoomNotFoundAPIException
from indico_vc_zoom.blueprint import blueprint
from indico_vc_zoom.cli import cli
from indico_vc_zoom.forms import VCRoomAttachForm, VCRoomForm
from indico_vc_zoom.http_api import DeleteVCRoomAPI
from indico_vc_zoom.models.zoom_meetings import ZoomMeeting
from indico_vc_zoom.util import iter_extensions, iter_user_identities, retrieve_principal, update_room_from_obj


class PluginSettingsForm(VCPluginSettingsFormBase):
    support_email = EmailField(_('Zoom email support'))

    api_key = StringField(_('API KEY'), [DataRequired()])

    api_secret = StringField(_('API SECRET'), [DataRequired()])

    auto_mute = BooleanField(_('Auto mute'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('The Zoom clients will join the VC room muted by default '))

    host_video = BooleanField(_('Host Video'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('Start video when the host joins the meeting.'))

    participant_video = BooleanField(_('Participant Video'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('Start video when participants join the meeting. '))

    join_before_host = BooleanField(_('Join Before Host'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('Allow participants to join the meeting before the host starts the meeting. Only used for scheduled or recurring meetings.'))

    #indico_room_prefix = IntegerField(_('Indico tenant prefix'), [NumberRange(min=0)],
    #                                  description=_('The tenant prefix for Indico rooms created on this server'))
    #room_group_name = StringField(_("Public rooms' group name"), [DataRequired()],
    #                              description=_('Group name for public videoconference rooms created by Indico'))
    num_days_old = IntegerField(_('VC room age threshold'), [NumberRange(min=1), DataRequired()],
                                description=_('Number of days after an Indico event when a videoconference room is '
                                              'considered old'))
    max_rooms_warning = IntegerField(_('Max. num. VC rooms before warning'), [NumberRange(min=1), DataRequired()],
                                     description=_('Maximum number of rooms until a warning is sent to the managers'))
    zoom_phone_link = URLField(_('ZoomVoice phone number'),
                                description=_('Link to the list of ZoomVoice phone numbers'))
    
    creation_email_footer = TextAreaField(_('Creation email footer'), widget=CKEditorWidget(),
                                          description=_('Footer to append to emails sent upon creation of a VC room'))


class ZoomPlugin(VCPluginMixin, IndicoPlugin):
    """Zoom

    Videoconferencing with Zoom
    """
    configurable = True
    settings_form = PluginSettingsForm
    vc_room_form = VCRoomForm
    vc_room_attach_form = VCRoomAttachForm
    friendly_name = 'Zoom'

    def init(self):
        super(ZoomPlugin, self).init()
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.js', WPVCEventPage)
        self.inject_bundle('main.js', WPVCManageEvent)
        HTTPAPIHook.register(DeleteVCRoomAPI)

    @property
    def default_settings(self):
        return dict(VCPluginMixin.default_settings, **{
            'support_email': config.SUPPORT_EMAIL,
            'api_key': '',
            'api_secret': '',
            #'indico_room_prefix': 10,
            'auto_mute':True,
            'host_video':False,
            'participant_video':True,
            'join_before_host':True,
            #'room_group_name': 'Indico',
            # we skip identity providers in the default list if they don't support get_identity.
            # these providers (local accounts, oauth) are unlikely be the correct ones to integrate
            # with the zoom infrastructure.
            'num_days_old': 5,
            'max_rooms_warning': 5000,
            'zoom_phone_link': None,
            'creation_email_footer': None
        })

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_logo.png')

    @property
    def icon_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_logo.png')

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def update_data_association(self, event, vc_room, event_vc_room, data):
        super(ZoomPlugin, self).update_data_association(event, vc_room, event_vc_room, data)

        event_vc_room.data.update({key: data.pop(key) for key in [
            'show_autojoin',
            'show_phone_numbers'
        ]})

        flag_modified(event_vc_room, 'data')

    def update_data_vc_room(self, vc_room, data):
        super(ZoomPlugin, self).update_data_vc_room(vc_room, data)

        for key in ['description', 'owner', 'auto_mute', 'host_video', 'participant_video', 'join_before_host']:
            if key in data:
                vc_room.data[key] = data.pop(key)

        flag_modified(vc_room, 'data')

    def create_room(self, vc_room, event):
        """Create a new Zoom room for an event, given a VC room.

        In order to create the Zoom room, the function will try to do so with
        all the available identities of the user based on the authenticators
        defined in Zoom plugin's settings, in that order.

        :param vc_room: VCRoom -- The VC room from which to create the Zoom
                        room
        :param event: Event -- The event to the Zoom room will be attached
        """
        client = ZoomIndicoClient(self.settings)
        #owner = retrieve_principal(vc_room.data['owner'])
        owner= session.user  
        user_id=owner.email
        topic=vc_room.name
        time_zone=event.timezone
        start=event.start_dt_local
        end=event.end_dt
        topic=vc_room.data['description']
        type_meeting=2
        host_video=self.settings.get('host_video')
        participant_video=self.settings.get('participant_video')
        join_before_host=self.settings.get('join_before_host')
        mute_upon_entry=self.settings.get('auto_mute')


        meeting_obj = client.create_meeting(user_id=user_id,
                                            type=type_meeting,
                                            start_time=start,
                                            topic=topic,
                                            timezone=time_zone,
                                            host_video=host_video,
                                            participant_video=participant_video,
                                            join_before_host=join_before_host,
                                            mute_upon_entry=mute_upon_entry)

        if not meeting_obj:
            raise VCRoomNotFoundError(_("Could not find newly created room in Zoom"))
        vc_room.data.update({
            'zoom_id': unicode(meeting_obj['id']),
            'url': meeting_obj['join_url'],
            'start_url':meeting_obj['start_url']
        })

        flag_modified(vc_room, 'data')
        vc_room.zoom_meeting = ZoomMeeting(vc_room_id=vc_room.id, meeting=meeting_obj['id'],
                                                 owned_by_user=owner, url_zoom=meeting_obj['join_url'])
        self.notify_owner_start_url(vc_room)
              

    def update_room(self, vc_room, event):
        pass

    def refresh_room(self, vc_room, event):
        pass

    def delete_room(self, vc_room, event):
        client = ZoomIndicoClient(self.settings)
        zoom_id = vc_room.data['zoom_id']
        client.delete_meeting(zoom_id)
        

    def get_meeting(self, vc_room):
        client = ZoomIndicoClient(self.settings)
        return client.get_meeting(vc_room.data['zoom_id'])

    def get_blueprints(self):
        return blueprint

    def get_vc_room_form_defaults(self, event):
        defaults = super(ZoomPlugin, self).get_vc_room_form_defaults(event)
        defaults.update({
            'show_autojoin': True,
            'show_phone_numbers': True,
            'owner_user': session.user
        })

        return defaults

    def get_vc_room_attach_form_defaults(self, event):
        defaults = super(ZoomPlugin, self).get_vc_room_attach_form_defaults(event)
        defaults.update({
            'show_autojoin': True,
            'show_phone_numbers': True
        })
        return defaults

    def can_manage_vc_room(self, user, room):
        return user == room.zoom_meeting.owned_by_user or super(ZoomPlugin, self).can_manage_vc_room(user, room)

    def _merge_users(self, target, source, **kwargs):
        super(ZoomPlugin, self)._merge_users(target, source, **kwargs)
        for ext in ZoomMeeting.find(owned_by_user=source):
            ext.owned_by_user = target
            flag_modified(ext.vc_room, 'data')

    def get_notification_cc_list(self, action, vc_room, event):
        return {vc_room.zoom_meeting.owned_by_user.email}


    def notify_owner_start_url(self, vc_room):
        user = vc_room.zoom_meeting.owned_by_user
        to_list = {user.email}

        template_module = get_template_module('vc_zoom:emails/notify_start_url.html', plugin=ZoomPlugin.instance, vc_room=vc_room, event=None,
                                         vc_room_event=None, user=user)

        email = make_email(to_list, template=template_module, html=True)
        send_email(email, None, 'Zoom') 
