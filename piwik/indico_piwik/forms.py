from wtforms import BooleanField, IntegerField, StringField

from indico.web.forms.base import IndicoForm
from MaKaC.i18n import _


class SettingsForm(IndicoForm):
    enabled = BooleanField(_("Enable statistics collection"), default=True)
    cache_enabled = BooleanField(_("Enable report caching"), default=True)
    cache_ttl = IntegerField(_("Report caching TTL (seconds)"), default=3600)
    js_hook_enabled = BooleanField(_("Enable conference and contribution view tracking"), default=True)
    download_tracking_enabled = BooleanField(_("Enable material download tracking"), default=True)
    server_url = StringField(_("Piwik general server URL (piwik.php)"), default='//127.0.0.1/piwik/')
    server_api_url = StringField(_("Piwik API server URL (index.php)"), default='//127.0.0.1/piwik/')
    user_only_server_url = BooleanField(_("Use only the general URL for all requests"), default=True)
    server_token = StringField(_("Piwik API token"))
    site_id_general = StringField(_("Piwik site ID (general)"), default='1')
    site_id_events = StringField(_("Piwik site ID (events)"), default='2')
