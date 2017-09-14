# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from flask_pluginengine import current_plugin, render_plugin_template


def render_engine_or_search_template(template_name, **context):
    """Renders a template from the engine plugin or the search plugin

    If the template is available in the engine plugin, it's taken
    from there, otherwise the template from this plugin is used.

    :param template_name: name of the template
    :param context: the variables that should be available in the
                    context of the template.
    """
    from indico_search.plugin import SearchPlugin
    assert current_plugin == SearchPlugin.instance

    templates = ('{}:{}'.format(SearchPlugin.instance.engine_plugin.name, template_name),
                 template_name)
    return render_plugin_template(templates, **context)
