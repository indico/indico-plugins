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
        credentials: inds_metrics_xxxxxx
    # this is only needed in development setups
    tls_config:
      insecure_skip_verify: true
```
