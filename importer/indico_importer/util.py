# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals


def convert_dt_tuple(dt_tuple):
    split_datetime = dt_tuple[0].split('T')
    if len(split_datetime) > 1:
        return {'date': dt_tuple[0].split('T')[0],
                'time': dt_tuple[0].split('T')[1]}
    else:
        return {'date': dt_tuple[0].split('T')[0],
                'time': '00:00'}
