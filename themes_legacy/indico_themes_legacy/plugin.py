# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import os

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint


class LegacyThemesPlugin(IndicoPlugin):
    """Legacy Themes

    Provides legacy event themes
    """

    def init(self):
        super().init()
        self.connect(signals.plugin.get_event_themes_files, self._get_themes_yaml)

    def get_blueprints(self):
        return IndicoPluginBlueprint(self.name, __name__)

    def _get_themes_yaml(self, sender, **kwargs):
        return os.path.join(self.root_path, 'themes-legacy.yaml')
