# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_previewer_jupyter.controllers import RHEventPreviewIPyNB


blueprint = IndicoPluginBlueprint('previewer_jupyter', __name__)
blueprint.add_url_rule('/preview/ipynb/<int:attachment_id>', 'preview_ipynb', RHEventPreviewIPyNB)
