# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_storage_s3.controllers import RHBuckets


blueprint = IndicoPluginBlueprint('storage_s3', __name__, url_prefix='/api/plugin/s3')
blueprint.add_url_rule('/buckets', 'buckets', RHBuckets)
