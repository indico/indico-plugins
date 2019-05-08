# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
