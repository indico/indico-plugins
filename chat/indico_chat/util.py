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
