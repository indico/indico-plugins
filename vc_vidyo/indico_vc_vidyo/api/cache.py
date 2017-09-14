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

from zeep.cache import Base

from indico.legacy.common.cache import GenericCache


DEFAULT_CACHE_TTL = 24 * 3600


class ZeepCache(Base):
    _instance = None

    def __init__(self, duration=DEFAULT_CACHE_TTL):
        self._cache = GenericCache("ZeepCache")
        self._duration = duration

    def get(self, url):
        self._cache.get(url)

    def add(self, url, content):
        self._cache.set(url, content, self._duration)
