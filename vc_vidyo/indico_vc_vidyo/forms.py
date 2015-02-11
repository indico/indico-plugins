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

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import StringField, TextAreaField
from wtforms.validators import DataRequired

from indico.web.forms.base import IndicoForm
from indico.util.i18n import _
from indico.web.forms.fields import SingleUserField


class VCRoomForm(IndicoForm):
    name = StringField(_('Name'), [DataRequired()], description=_('The name of the room'))
    description = TextAreaField(_('Description'), description=_('The description of the room'))
    moderator = SingleUserField(_('Moderator'), description=_('The moderator of the room'))
    auto_mute = BooleanField(_('Auto mute'),
                             description=_('The VidyoDesktop clients will join the meeting muted by default'
                                           '(audio and video)'))
