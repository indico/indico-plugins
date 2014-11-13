# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from indico.core.db import db
from indico.util.console import cformat
from indico_zodbimport import Importer, convert_to_unicode

from indico_piwik import PiwikPlugin


class PiwikImporter(Importer):
    plugins = {'piwik'}

    def migrate(self):
        self.migrate_settings()

    def migrate_settings(self):
        print cformat('%{white!}migrating settings')
        PiwikPlugin.settings.delete_all()
        type_opts = self.zodb_root['plugins']['statistics']._PluginBase__options
        settings_map = {'cacheEnabled': 'cache_enabled',
                        'cacheTTL': 'cache_ttl'}
        for old, new in settings_map.iteritems():
            PiwikPlugin.settings.set(new, type_opts[old].getValue())
        opts = self.zodb_root['plugins']['statistics']._PluginType__plugins['piwik']._PluginBase__options
        settings_map = {'serverAPIUrl': 'server_api_url',
                        'serverUrl': 'server_url',
                        'serverSiteID': 'site_id_general',
                        'serverTok': 'server_token',
                        'useOnlyServerURL': 'use_only_server_url',
                        'jsHookEnabled': 'enabled_for_events',
                        'downloadTrackingEnabled': 'enabled_for_downloads'}
        for old, new in settings_map.iteritems():
            value = opts[old].getValue()
            if isinstance(value, basestring):
                value = convert_to_unicode(value).strip()
            PiwikPlugin.settings.set(new, value)
        db.session.commit()
