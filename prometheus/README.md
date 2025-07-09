# Indico Prometheus Plugin

This plugin exposes a `/metrics` endpoint which provides Prometheus-compatible output.

![](https://raw.githubusercontent.com/indico/indico-plugins/master/prometheus/screenshot.png)

## prometheus.yml
```yaml
scrape_configs:
  - job_name: indico_stats
    metrics_path: /metrics
    scheme: https
    static_configs:
      - targets:
        - yourindicoserver.example.com
    # it is recommended that you set a bearer token in the config
    authorization:
        credentials: xxxxxx
    # this is only needed in development setups
```

If you're doing development you may want to add this under `scrape_configs`:
```yaml
    tls_config:
      insecure_skip_verify: false
```

## Changelog

### 3.3.2

- Fix errors if livesync plugin is installed but not enabled and do not expose livesync-related
  metrics at all in that case
- Use latest prometheus-client library

### 3.3.1

- Use latest prometheus-client library
- Ensure that only one `Content-type` header (`text/plain`) is sent

### 3.3

- Support (and require) Python 3.12

### 3.2.1

- Support Python 3.11
- Use latest prometheus-client library

### 3.2

- Initial release for Indico 3.2
