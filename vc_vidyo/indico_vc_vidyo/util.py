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

from indico.util.user import retrieve_principals


def get_auth_users():
    """Returns a list of authorized users

    :return: list of Avatar/Group objects
    """
    from indico_vc_vidyo.plugin import VidyoPlugin
    return retrieve_principals(VidyoPlugin.settings.get('authorized_users'))


def is_auth_user(user):
    """Checks if a user is authorized"""
    return any(principal.containsUser(user) for principal in get_auth_users())
