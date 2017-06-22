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

from indico.util.i18n import _
from indico.util.placeholders import Placeholder


class FirstNamePlaceholder(Placeholder):
    name = 'first_name'
    description = _("First name of the person")

    @classmethod
    def render(cls, event, registration):
        return registration.first_name


class LastNamePlaceholder(Placeholder):
    name = 'last_name'
    description = _("Last name of the person")

    @classmethod
    def render(cls, event, registration):
        return registration.last_name


class EventIDPlaceholder(Placeholder):
    name = 'event_id'
    description = _("The ID of the event")

    @classmethod
    def render(cls, event, registration):
        return event.id


class IDPlaceholder(Placeholder):
    name = 'registration_id'
    description = _("The ID of the registration")

    @classmethod
    def render(cls, event, registration):
        return registration.friendly_id
