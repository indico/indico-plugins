# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import make_response, request
from flask_pluginengine import current_plugin
from prometheus_client.exposition import _bake_output
from prometheus_client.registry import REGISTRY
from werkzeug.exceptions import ServiceUnavailable, Unauthorized

from indico.core.cache import make_scoped_cache
from indico.web.rh import RH, custom_auth

from indico_prometheus.metrics import update_metrics


cache = make_scoped_cache('prometheus_metrics')


@custom_auth
class RHMetrics(RH):
    def _check_access(self):
        if not current_plugin.settings.get('enabled'):
            raise ServiceUnavailable
        token = current_plugin.settings.get('token')
        if token and token != request.bearer_token:
            raise Unauthorized

    def _process(self):
        accept_header = request.headers.get('Accept')
        accept_encoding_header = request.headers.get('Accept-Encoding')
        metrics = cache.get('metrics')

        cached = False
        if metrics:
            cached = True
            status, headers, output = metrics
        else:
            update_metrics(
                current_plugin.settings.get('active_user_age'), cache, current_plugin.settings.get('heavy_cache_ttl')
            )
            status, headers, output = _bake_output(
                REGISTRY, accept_header, accept_encoding_header, request.args, False
            )
            cache.set('metrics', (status, headers, output), timeout=current_plugin.settings.get('global_cache_ttl'))

        resp = make_response(output)
        resp.status = status

        resp.headers['X-Cached'] = 'yes' if cached else 'no'
        resp.headers.extend(headers)

        return resp
