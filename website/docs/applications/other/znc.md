---
title: "ZNC"
---

Homepage: [https://wiki.znc.in/ZNC](https://wiki.znc.in/ZNC)

IRC bouncer that stays connected to IRC networks, buffers messages, and replays them when you reconnect.

## Usage

Set `znc_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web admin interface is available at `http://ansible_nas_host_or_ip:6677`.

If you want to access ZNC externally, set `znc_available_externally: true`.

## Specific Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `znc_data_directory` | `{{ docker_home }}/znc` | Configuration and module storage |
| `znc_user_id` | `0` | Container user ID |
| `znc_group_id` | `0` | Container group ID |
| `znc_hostname` | `znc` | Container hostname |
| `znc_port` | `6677` | Web admin / IRC port |
| `znc_memory` | `1g` | Memory limit |
| `znc_user_password` | *(required)* | Admin web UI password |
| `znc_user_nick` | `user` | Primary IRC nick |
| `znc_user_altnick` | `user_` | Alternate nick |
| `znc_user_ident` | `user` | Ident string |
| `znc_user_real_name` | `User Name` | Real name field |

**Required secret:** `znc_user_password` defaults to empty and must be set in your inventory (ideally vault-encrypted).

On first run, ZNC creates a default configuration. Access the web admin at `http://<nas>:6677` to configure networks, channels, and modules. The configuration persists in `znc_data_directory`.

ZNC does not expose an HTTP service for Uptime Kuma monitoring (it's an IRC service), so it does not set `znc_uptime_kuma_monitor`.
