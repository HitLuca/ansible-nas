---
title: "Alloy"
---

Homepage: [https://grafana.com/docs/alloy/latest/](https://grafana.com/docs/alloy/latest/)

Docker image: [Alloy](https://hub.docker.com/r/grafana/alloy)

Grafana Alloy ships the contents of local Docker logs to a Grafana Loki instance. It replaces Promtail, which reached end-of-life.

## Usage

Set `alloy_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, alongside `loki_enabled: true`.

Alloy has no web interface. To see what it's doing, look at the container logs from your Ansible-NAS shell:

```bash
docker logs alloy -f
```
