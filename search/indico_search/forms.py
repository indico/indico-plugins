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

from wtforms.ext.dateutil.fields import DateField
from wtforms.fields.core import StringField, SelectField
from wtforms.validators import Optional

from indico.web.forms.base import IndicoForm

from indico_search import _


FIELD_CHOICES = [('', _('Anywhere')),
                 ('title', _('Title')),
                 ('abstract', _('Description/Abstract')),
                 ('author', _('Author/Speaker')),
                 ('affiliation', _('Affiliation')),
                 ('keyword', _('Keyword'))]


class SearchForm(IndicoForm):
    phrase = StringField(_('Phrase'))
    field = SelectField(_('Search in'), choices=FIELD_CHOICES, default='')
    start_date = DateField('Start Date', [Optional()], parse_kwargs={'dayfirst': True})
    end_date = DateField('End Date', [Optional()], parse_kwargs={'dayfirst': True})
