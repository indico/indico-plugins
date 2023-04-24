# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from wtforms.fields import StringField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin
from indico.core.settings.converters import TimedeltaConverter
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import TimeDeltaField

from indico_prometheus import _
from indico_prometheus.blueprint import blueprint


class PluginSettingsForm(IndicoForm):
    cache_ttl = TimeDeltaField(
        _('Cache TTL'),
        [DataRequired()],
        description=_('TTL for cache'),
        units=('seconds', 'minutes', 'hours')
    )
    token = StringField(
        _('Bearer Token'),
        [Optional()],
        description=_("Authentication bearer token for Prometheus. Please note that it should be "
                      "preceded by 'inds_metrics_'")
    )
    active_user_age = TimeDeltaField(
        _('Max. Active user age'),
        [DataRequired()],
        description=_('Time since login after which a user is not considered active anymore'),
        units=('minutes', 'hours', 'days')
    )


class PrometheusPlugin(IndicoPlugin):
    """Prometheus

    Provides a metrics endpoint which can be queried by Prometheus
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'cache_ttl': timedelta(minutes=5),
        'token': '',
        'active_user_age': timedelta(hours=48)
    }
    settings_converters = {
        'cache_ttl': TimedeltaConverter,
        'active_user_age': TimedeltaConverter
    }

    def get_blueprints(self):
        return blueprint
