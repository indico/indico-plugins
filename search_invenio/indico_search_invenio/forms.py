# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
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

from wtforms.fields.core import SelectField

from indico_search import SearchForm
from indico_search_invenio import _


COLLECTION_CHOICES = [('', _('Both (Events + Contributions)')),
                      ('events', _('Events')),
                      ('contributions', _('Contributions'))]
SORT_ORDER_CHOICES = [('a', _('Oldest first')),
                      ('d', _('Newest first'))]


class InvenioSearchForm(SearchForm):
    collection = SelectField(_('Search for'), choices=COLLECTION_CHOICES, default='')
    sort_order = SelectField(_('Sort order'), choices=SORT_ORDER_CHOICES, default='d')
