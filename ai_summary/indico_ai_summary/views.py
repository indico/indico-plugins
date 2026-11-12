# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import WPJinjaMixinPlugin
from indico.modules.categories.views import WPCategoryManagement


class WPCategoryManagePrompts(WPJinjaMixinPlugin, WPCategoryManagement):
    pass
