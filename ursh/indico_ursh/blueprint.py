# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_ursh.controllers import RHCustomShortURLPage, RHGetShortURL, RHShortURLPage


blueprint = IndicoPluginBlueprint('ursh', 'indico_ursh')
blueprint.add_url_rule('/ursh', 'get_short_url', RHGetShortURL, methods=('POST',))
blueprint.add_url_rule('/url-shortener', 'shorten_url', RHShortURLPage)
blueprint.add_url_rule('/event/<confId>/manage/short-url', 'shorten_event_url', RHCustomShortURLPage,
                       methods=('GET', 'POST'))
