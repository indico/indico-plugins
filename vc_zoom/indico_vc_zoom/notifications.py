# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.notifications import make_email, send_email
from indico.util.user import principal_from_identifier
from indico.web.flask.templating import get_template_module


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
    send_email(email)
