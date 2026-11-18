---
title: "Grafana"
---

Homepage: [https://grafana.com/](https://grafana.com/)

Docker image: [Grafana](https://hub.docker.com/r/grafana/grafana)

Query, visualize, alert on, and understand your data no matter where it's stored. With Grafana you can create, explore, and share all of your data through beautiful, flexible dashboards.

## Usage

Set `grafana_enabled: true` and a `grafana_admin_password` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Grafana's web interface can be found at [http://ansible_nas_host_or_ip:3000](http://ansible_nas_host_or_ip:3000).

When `prometheus_enabled` is true, the Prometheus data source and the Ansible-NAS overview dashboard are provisioned automatically. When `loki_enabled` is true, the Loki data source is provisioned too.
