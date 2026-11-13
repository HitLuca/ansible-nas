---
title: "Seerr"
---

Homepage: [https://docs.seerr.dev](https://docs.seerr.dev)

Docker Container: [https://github.com/seerr-team/seerr/pkgs/container/seerr](https://github.com/seerr-team/seerr/pkgs/container/seerr)

Seerr is a free and open source software application for managing requests for your media library. It integrates with your existing services, such as Sonarr, Radarr, Plex, Jellyfin and Emby! It's the maintained successor of Overseerr and Jellyseerr.

## Usage

Set `seerr_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Seerr web interface can be found at [http://ansible_nas_host_or_ip:5055](http://ansible_nas_host_or_ip:5055).

## Migrating from the Overseerr role

This role was previously named `overseerr`. To migrate an existing deployment:

1. Rename `overseerr_enabled` to `seerr_enabled` in your inventory.
2. Remove the old container, which still holds port 5055: `docker rm -f overseerr`.
3. Move the data directory: the role now stores its config in `seerr/config` under `docker_home`, where it used to use `overseerr/config`. Either move the old folder (`mv overseerr seerr`) or point `seerr_data_directory` at the old path. Back the folder up first so you can roll back.

Seerr migrates an existing Overseerr database automatically the first time it starts. Before that first start the role chowns the config folder to UID 1000, the user Seerr runs as.
