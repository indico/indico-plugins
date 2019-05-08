# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
