# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from indico.util.string import unicode_to_ascii


INVALID_JID_CHARS = re.compile(r'[^-!#()*+,.=^_a-z0-9]')
WHITESPACE = re.compile(r'\s+')


# TODO: implement the XMPP gateway
def create_room(room):
    """Creates a `Chatroom` on the XMPP server."""
    print 'create_room / not implemented yet'


def update_room(room):
    """Updates a `Chatroom` on the XMPP server."""
    print 'update_room / not implemented yet'


def delete_room(room):
    """Deletes a `Chatroom` from the XMPP server."""
    print 'delete_room / not implemented yet'


def generate_jid(name):
    """Generates a valid JID node identifier from a name"""
    jid = unicode_to_ascii(name).lower()
    jid = WHITESPACE.sub('-', jid)
    jid = INVALID_JID_CHARS.sub('', jid)
    return jid.strip()[:256]
