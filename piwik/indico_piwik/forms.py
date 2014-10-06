from wtforms import BooleanField, IntegerField, StringField

from indico.web.forms.base import IndicoForm
from MaKaC.i18n import _


class SettingsForm(IndicoForm):
    enabled = BooleanField(_("Enable statistics collection"))
    cache_enabled = BooleanField(_("Enable report caching"))
    cache_ttl = IntegerField(_("Report caching TTL (seconds)"))
    js_hook_enabled = BooleanField(_("Enable conference and contribution view tracking"))
    download_tracking_enabled = BooleanField(_("Enable material download tracking"))
    server_url = StringField(_("Piwik general server URL (piwik.php)"))
    server_api_url = StringField(_("Piwik API server URL (index.php)"))
    use_only_server_url = BooleanField(_("Use only the general URL for all requests"))
    server_token = StringField(_("Piwik API token"))
    site_id_general = StringField(_("Piwik site ID (general)"))
    site_id_events = StringField(_("Piwik site ID (events)"))
