from __future__ import unicode_literals

from indico.web.flask.templating import get_template_module
from indico.core.notifications import make_email, send_email
from indico.util.user import principal_from_identifier


def notify_host_start_url(vc_room):
    from indico_vc_zoom.plugin import ZoomPlugin

    user = principal_from_identifier(vc_room.data['host'])
    to_list = {user.email}

    template_module = get_template_module(
        'vc_zoom:emails/notify_start_url.html',
        plugin=ZoomPlugin.instance,
        vc_room=vc_room,
        user=user
    )

    email = make_email(to_list, template=template_module, html=True)
    send_email(email, None, 'Zoom')


def notify_new_host(actor, vc_room):
    from indico_vc_zoom.plugin import ZoomPlugin

    template_module = get_template_module(
        'vc_zoom:emails/notify_new_host.html',
        plugin=ZoomPlugin.instance,
        vc_room=vc_room,
        actor=actor
    )

    new_host = principal_from_identifier(vc_room.data['host'])
    email = make_email({new_host.email}, cc_list={actor.email}, template=template_module, html=True)
    send_email(email, None, 'Zoom')
