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

import pytest

from indico_livesync.util import make_compound_id


@pytest.mark.parametrize(('ref', 'expected'), (
    ({'type': 'event', 'event_id': '123'}, '123'),
    ({'type': 'contribution', 'event_id': '123', 'contrib_id': '456'}, '123.456'),
    ({'type': 'subcontribution', 'event_id': '123', 'contrib_id': '456', 'subcontrib_id': '789'}, '123.456.789'),
))
def test_make_compound_id(ref, expected):
    assert make_compound_id(ref) == expected


@pytest.mark.parametrize('ref_type', ('unknown', 'category'))
def test_make_compound_id_errors(ref_type):
    with pytest.raises(ValueError):
        make_compound_id({'type': ref_type})
