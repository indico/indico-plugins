# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.errors import IndicoError

from indico_chat import _


def check_config(quiet=False):
    """Checks if all required config options are set

    :param quiet: if True, return the result as a bool, otherwise
                  raise `IndicoError` if any setting is missing
    """
    from indico_chat.plugin import ChatPlugin
    settings = ChatPlugin.settings.get_all()
    missing = not all(settings[x] for x in ('server', 'muc_server', 'bot_jid', 'bot_password'))
    if missing and not quiet:
        raise IndicoError(_('Chat plugin is not configured properly'))
    return not missing


def is_chat_admin(user):
    """Checks if a user is a chat admin"""
    from indico_chat.plugin import ChatPlugin
    return ChatPlugin.settings.acls.contains_user('admins', user)
