# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from zeep.cache import Base

from indico.core.cache import make_scoped_cache


DEFAULT_CACHE_TTL = 24 * 3600


class ZeepCache(Base):
    _instance = None

    def __init__(self, duration=DEFAULT_CACHE_TTL):
        self._cache = make_scoped_cache('zeep')
        self._duration = duration

    def get(self, url):
        self._cache.get(url)

    def add(self, url, content):
        self._cache.set(url, content, timeout=self._duration)
