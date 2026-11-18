---
title: "Prometheus"
---

Homepage: [https://prometheus.io/](https://prometheus.io/)

Docker image: [Prometheus](https://hub.docker.com/r/prom/prometheus)

Prometheus is a time-series database that scrapes and stores metrics. This role also runs the collectors that feed it: Telegraf (host and Docker metrics) and the smartctl exporter (disk health and temperature).

## Usage

Set `prometheus_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

To also track your internet connection speed, enable `prometheus_speedtest_enabled: true`. To access Prometheus externally, set `prometheus_available_externally: true`.

Prometheus can be found at [http://ansible_nas_host_or_ip:9090](http://ansible_nas_host_or_ip:9090).
