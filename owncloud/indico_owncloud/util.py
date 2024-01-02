# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

def is_configured():
    """Check whether the plugin is properly configured."""
    from indico_owncloud.plugin import OwncloudPlugin

    return bool(OwncloudPlugin.settings.get('filepicker_url'))


def get_filepicker_url():
    from indico_owncloud.plugin import OwncloudPlugin

    return OwncloudPlugin.settings.get('filepicker_url').rstrip('/')
