---
title: "qBittorrent"
---

Homepage: [https://www.qbittorrent.org/](https://www.qbittorrent.org/)

qBittorrent is a free, open-source BitTorrent client with a built-in web UI, RSS support and a search/plugin ecosystem. It is the most widely used torrent client in *arr stacks.

## Usage

Set `qbittorrent_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

qBittorrent's web interface can be found at [http://ansible_nas_host_or_ip:8019](http://ansible_nas_host_or_ip:8019). A temporary password for the `admin` user is printed to the container log on first start — log in with it and set your own password in the web UI, otherwise a new one is generated on every restart.

Downloads land in `{{ downloads_root }}` (mounted at `/downloads`); the watch folder is `{{ torrents_root }}` (mounted at `/watch`). Point qBittorrent's "Watched folders" at `/watch` to use it.

Only the web UI port is published by default, so qBittorrent runs as a passive node. To seed actively, also publish the torrenting port (`6881` tcp/udp) and set `TORRENTING_PORT` to match.

## Specific Configuration

Set `qbittorrent_user_id` and `qbittorrent_group_id` (both default to `0`) to run as a different user.

See [https://github.com/linuxserver/docker-qbittorrent](https://github.com/linuxserver/docker-qbittorrent) for the full image documentation.
