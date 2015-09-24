# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from indico.core.plugins import WPJinjaMixinPlugin
from MaKaC.webinterface.pages.conferences import WPConferenceDefaultDisplayBase, WPConferenceModifBase


class WPChatEventPage(WPJinjaMixinPlugin, WPConferenceDefaultDisplayBase):
    menu_entry_plugin = 'chat'
    menu_entry_name = 'chatrooms'

    def __init__(self, rh, conf, **kwargs):
        WPConferenceDefaultDisplayBase.__init__(self, rh, conf, **kwargs)
        self._conf = conf
        self._aw = rh.getAW()

    def _getBody(self, params):
        return self._getPageContent(params)

    def getCSSFiles(self):
        return WPConferenceDefaultDisplayBase.getCSSFiles(self) + self._asset_env['eventservices_sass'].urls()

    def getJSFiles(self):
        return WPConferenceDefaultDisplayBase.getJSFiles(self) + self._asset_env['modules_event_display_js'].urls()


class WPChatEventMgmt(WPJinjaMixinPlugin, WPConferenceModifBase):
    sidemenu_option = 'chat-management'
