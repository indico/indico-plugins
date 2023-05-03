# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_prometheus.controllers import RHMetrics


blueprint = IndicoPluginBlueprint('prometheus', __name__)

blueprint.add_url_rule('/metrics', 'metrics', RHMetrics)
