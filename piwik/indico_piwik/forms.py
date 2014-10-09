from wtforms import BooleanField, IntegerField, StringField

from indico.util.i18n import _
from indico.web.forms.base import IndicoForm


class SettingsForm(IndicoForm):
    enabled = BooleanField(_("Enable general statistics tracking"))
    enabled_for_events = BooleanField(_("Enable statistics tracking for events and contributions"))
    enabled_for_downloads = BooleanField(_("Enable material download tracking"))
    cache_enabled = BooleanField(_("Enable report caching"))
    cache_ttl = IntegerField(_("Report caching TTL (seconds)"))
    server_url = StringField(_("Piwik general server URL (piwik.php)"))
    server_api_url = StringField(_("Piwik API server URL (index.php)"))
    use_only_server_url = BooleanField(_("Use only the general URL for all requests"))
    server_token = StringField(_("Piwik API token"))
    site_id_general = StringField(_("Piwik site ID (general)"))
    site_id_events = StringField(_("Piwik site ID (events)"))
