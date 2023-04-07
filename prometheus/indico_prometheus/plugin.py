# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields import IntegerField, StringField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin
from indico.web.forms.base import IndicoForm

from indico_prometheus import _
from indico_prometheus.blueprint import blueprint


class PluginSettingsForm(IndicoForm):
    cache_ttl = IntegerField(_('Cache TTL (s)'), [DataRequired()], description=_('TTL for cache (seconds)'))
    token = StringField(
        _('Bearer Token'),
        [Optional()],
        description=_("Authentication bearer token for Prometheus. Please note that it should be "
                      "preceded by 'inds_metrics_'")
    )
    active_user_hours = IntegerField(
        _('Max. Active user age (h)'),
        [DataRequired()],
        description=_('Number of hours since login after which a user is not considered active anymore')
    )


class PrometheusPlugin(IndicoPlugin):
    """Prometheus

    Provides a metrics endpoint which can be queried by Prometheus
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'cache_ttl': 120,
        'token': '',
        'active_user_hours': 48
    }

    def get_blueprints(self):
        return blueprint
