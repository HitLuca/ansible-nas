---
title: "Sickchill"
---

Homepage: [https://sickchill.github.io/](https://sickchill.github.io/)

TV show management for Usenet and BitTorrent — automatic episode searching, downloading, and sorting.

## Usage

Set `sickchill_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web interface is available at `http://ansible_nas_host_or_ip:8081`.

If you want to access Sickchill externally, set `sickchill_available_externally: true`.

## Specific Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `sickchill_config_directory` | `{{ docker_home }}/sickchill/config` | Configuration storage |
| `sickchill_tv_directory` | `{{ tv_root }}` | TV show library |
| `sickchill_downloads_directory` | `{{ downloads_root }}/completed` | Completed downloads |
| `sickchill_user_id` | `0` | Container user ID |
| `sickchill_group_id` | `0` | Container group ID |
| `sickchill_port` | `8081` | Web UI port |
| `sickchill_hostname` | `sickchill` | Container hostname |
| `sickchill_memory` | `1g` | Memory limit |

The role pins the official `sickchill/sickchill` image (migrated from the archived `linuxserver/sickchill` image in v3.0.0). The database migrates automatically on upgrade, but back up `/config` first.

Configure indexers (Jackett, Prowlarr) and download clients (Sabnzbd, qBittorrent, Transmission) in the Sickchill web UI after first login.
