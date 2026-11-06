---
title: "Seerr (Overseerr)"
---

Homepage: [https://docs.seerr.dev](https://docs.seerr.dev)

Docker Container: [https://github.com/seerr-team/seerr/pkgs/container/seerr](https://github.com/seerr-team/seerr/pkgs/container/seerr)

Seerr is a free and open source software application for managing requests for your media library. It integrates with your existing services, such as Sonarr, Radarr, Plex, Jellyfin and Emby! It's the maintained successor of Overseerr and Jellyseerr.

## Usage

Set `overseerr_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file. The role and its variables keep the `overseerr` name so existing inventories keep working.

The Seerr web interface can be found at [http://ansible_nas_host_or_ip:5055](http://ansible_nas_host_or_ip:5055).

## Upgrading from Overseerr

Earlier versions of this role ran the archived `sctx/overseerr` image. Seerr migrates the existing config in `overseerr/config` automatically the first time it starts, and the role sets that folder's ownership to UID 1000, the user Seerr runs as. Back up `overseerr/config` before the first run so you can roll back if needed.
