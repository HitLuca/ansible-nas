---
title: "Hello World"
---

Homepage: [https://hub.docker.com/r/crccheck/hello-world](https://hub.docker.com/r/crccheck/hello-world)

Hello World is a tiny demo container that serves a static page over HTTP. Ansible-NAS ships it as the reference implementation for new roles: if this one starts, Docker and the playbook are wired up correctly.

## Usage

Set `hello_world_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The page is then reachable at `http://ansible_nas_host_or_ip:9999`. Set `hello_world_available_externally: true` to also expose it through Traefik at `hello_world.<your domain>` with a Let's Encrypt certificate.

## Specific Configuration

The container listens on port 8000 internally; `hello_world_port` is the host port it is published on. `hello_world_data_directory` is mounted at `/hello_world` inside the container. With `hello_world_uptime_kuma_monitor: true` (or `uptime_kuma_monitor_all_services: true` globally), an Uptime Kuma monitor is created for the published URL automatically.
