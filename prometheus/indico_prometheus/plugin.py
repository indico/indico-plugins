# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from wtforms.fields import BooleanField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin
from indico.core.settings.converters import TimedeltaConverter
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, TimeDeltaField
from indico.web.forms.widgets import SwitchWidget

from indico_prometheus import _
from indico_prometheus.blueprint import blueprint


class PluginSettingsForm(IndicoForm):
    enabled = BooleanField(
        _("Enabled"), [DataRequired()],
        description=_("Endpoint enabled. Turn this on once you set a proper bearer token."),
        widget=SwitchWidget()
    )
    global_cache_ttl = TimeDeltaField(
        _('Global Cache TTL'),
        [DataRequired()],
        description=_('TTL for "global" cache (everything)'),
        units=('seconds', 'minutes', 'hours')
    )
    heavy_cache_ttl = TimeDeltaField(
        _('Heavy Cache TTL'),
        [DataRequired()],
        description=_('TTL for "heavy" cache (more expensive queries such as attachments)'),
        units=('seconds', 'minutes', 'hours')
    )
    token = IndicoPasswordField(
        _('Bearer Token'),
        [Optional()],
        toggle=True,
        description=_('Authentication bearer token for Prometheus')
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
        'enabled': False,
        'global_cache_ttl': timedelta(minutes=5),
        'heavy_cache_ttl': timedelta(minutes=30),
        'token': '',
        'active_user_age': timedelta(hours=48)
    }
    settings_converters = {
        'global_cache_ttl': TimedeltaConverter,
        'heavy_cache_ttl': TimedeltaConverter,
        'active_user_age': TimedeltaConverter
    }

    def get_blueprints(self):
        return blueprint
