from wtforms import BooleanField, IntegerField

from indico.web.forms.base import IndicoForm


class SettingsForm(IndicoForm):
    cache_enabled = BooleanField('Enable report caching', default=True)
    cache_ttl = IntegerField('Report caching TTL (seconds)', default=3600)
