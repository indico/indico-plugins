# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask import request
from wtforms.fields.core import SelectField, StringField
from wtforms.validators import Optional

from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoDateField

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
    start_date = IndicoDateField('Start Date', [Optional()])
    end_date = IndicoDateField('End Date', [Optional()])

    def is_submitted(self):
        return 'search-phrase' in request.args
