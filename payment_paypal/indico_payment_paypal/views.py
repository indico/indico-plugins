# This file is part of the CERN Indico plugins.
# Copyright (C) 2014 - 2024 CERN
#
# The CERN Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License; see
# the LICENSE file for more details.

from indico.core.plugins import WPJinjaMixinPlugin
from indico.modules.events.views import WPConferenceDisplayBase


class WPPaymentEventPaypal(WPJinjaMixinPlugin, WPConferenceDisplayBase):
    menu_entry_name = 'registration'
