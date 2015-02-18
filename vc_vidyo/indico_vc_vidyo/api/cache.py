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

from suds.cache import Cache
from MaKaC.common.cache import GenericCache

DEFAULT_CACHE_TTL = 24 * 3600


class SudsCache(Cache):
    _instance = None

    def __init__(self, duration=DEFAULT_CACHE_TTL):
        self._cache = GenericCache("SudsCache")
        self._duration = duration

    def get(self, key):
        self._cache.get(key)

    def put(self, key, val):
        self._cache.set(key, val, self._duration)

    def purge(self, key):
        self._cache.delete(key)
