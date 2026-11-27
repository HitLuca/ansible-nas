---
title: "Netdata"
---

Homepage: [https://my-netdata.io/](https://my-netdata.io/)

Real-time system monitoring and observability platform with per-second metrics.

## Usage

Set `netdata_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web interface is available at `http://ansible_nas_host_or_ip:19999`.

If you want to access Netdata externally, set `netdata_available_externally: true`.

## Specific Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `netdata_hostname` | `netdata` | Hostname for Netdata |
| `netdata_port` | `19999` | Web UI port |
| `netdata_memory` | `1g` | Memory limit |

Netdata collects system metrics automatically. It can stream metrics to a central Netdata parent or to Prometheus via the Prometheus remote write endpoint (configure in the Netdata UI).

The container requires access to `/proc`, `/sys`, and `/var/run/docker.sock` for container monitoring, which the role configures automatically.
