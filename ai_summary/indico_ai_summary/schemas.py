# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from webargs import fields

from indico.core.marshmallow import mm
from indico.util.marshmallow import not_empty


class PromptSchema(mm.Schema):
    name = fields.String(required=True, validate=not_empty)
    text = fields.String(required=True, validate=not_empty)
