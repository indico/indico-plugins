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


def convert_dt_tuple(dt_tuple):
    split_datetime = dt_tuple[0].split('T')
    if len(split_datetime) > 1:
        return {'date': dt_tuple[0].split('T')[0],
                'time': dt_tuple[0].split('T')[1]}
    else:
        return {'date': dt_tuple[0].split('T')[0],
                'time': '00:00'}
