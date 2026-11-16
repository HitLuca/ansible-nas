---
title: "Dockhand"
---

Homepage: [https://dockhand.pro/](https://dockhand.pro/)

Docker Container: [https://hub.docker.com/r/fnsys/dockhand](https://hub.docker.com/r/fnsys/dockhand)

Docker management UI with real-time container control, Compose stack orchestration, terminals, logs, file browsing and backups.

## Usage

Set `dockhand_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Dockhand web interface can be found at [http://ansible_nas_host_or_ip:8099](http://ansible_nas_host_or_ip:8099).

Dockhand controls every container on the host: the role mounts the Docker socket read-write into its container. Authentication is disabled on first launch; open the UI and enable it under **Settings > Authentication** before anyone else can reach the port. The free edition gives every authenticated user full admin access.

If you want to access Dockhand externally, don't forget to set `dockhand_available_externally: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file. Only do this behind an authenticating reverse proxy or a VPN — an unauthenticated Dockhand with socket access is equivalent to root on the NAS.
