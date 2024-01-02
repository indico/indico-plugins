# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields import StringField
from wtforms.validators import DataRequired

from indico.web.forms.base import IndicoForm

from indico_livesync import _


class AgentForm(IndicoForm):
    name = StringField(_('Name'), [DataRequired()],
                       description=_('The name of the agent. Only used in the administration interface.'))
