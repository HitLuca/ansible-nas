---
title: "Spoolman"
---

Homepage: [https://github.com/Donkie/Spoolman](https://github.com/Donkie/Spoolman)

Docker Container: [https://hub.docker.com/r/donkieyo/spoolman](https://hub.docker.com/r/donkieyo/spoolman)

Spoolman keeps track of your inventory of 3D-printer filament spools. It stores
filament types, colours, spool weights and remaining material, and exposes a
REST API that slicers such as OctoPrint and Moonraker can query.

## Usage

Set `spoolman_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml`.

The web interface is at [http://ansible_nas_host_or_ip:7912](http://ansible_nas_host_or_ip:7912).

Setting `spoolman_available_externally: true` serves it through Traefik at
`https://spoolman.<ansible_nas_domain>`; this needs a wildcard DNS entry for
your domain. The app is then reachable without authentication unless you also
set `spoolman_authelia_enabled: true`, which puts the Authelia forward-auth
middleware in front of it. That requires the
[Authelia](../system-tools/authelia.md) role to be enabled and running.

Spoolman's data, including its SQLite database, lives in
`{{ spoolman_data_directory }}` (`spoolman` under your docker home).
