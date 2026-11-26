---
title: "Transmission with OpenVPN"
---

Homepage: [https://github.com/haugene/docker-transmission-openvpn](https://github.com/haugene/docker-transmission-openvpn)

Transmission BitTorrent client with built-in OpenVPN support for privacy.

## Usage

Set `transmission_with_openvpn_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web interface is available at `http://ansible_nas_host_or_ip:9091`.

If you want to access the web UI externally, set `transmission_with_openvpn_available_externally: true`.

## Specific Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `transmission_config_directory` | `{{ docker_home }}/transmission/config` | Configuration storage |
| `transmission_download_directory` | `{{ downloads_root }}` | Download directory |
| `transmission_watch_directory` | `{{ torrents_root }}` | Watch directory for .torrent files |
| `transmission_openvpn_user_id` | `0` | Container user ID |
| `transmission_openvpn_group_id` | `0` | Container group ID |
| `transmission_openvpn_ratio_limit_enabled` | `true` | Enable seed ratio limit |
| `transmission_openvpn_ratio_limit` | `2` | Stop seeding at this ratio |
| `transmission_openvpn_local_network` | `192.168.1.0/24` | Local network for web UI access without VPN |
| `transmission_openvpn_webui_port` | `9091` | Web UI port |
| `transmission_openvpn_external_port` | `51415` | Incoming peer port |
| `transmission_openvpn_proxy_port` | `3128` | Proxy port |
| `transmission_openvpn_hostname` | `transmission_openvpn` | Container hostname |
| `transmission_openvpn_memory` | `1g` | Memory limit |
| `openvpn_username` | *(required)* | VPN provider username |
| `openvpn_password` | *(required)* | VPN provider password |
| `openvpn_provider` | *(required)* | VPN provider name (e.g., `AWESOMEVPNPROVIDER`) |
| `openvpn_config` | *(required)* | VPN config/location (e.g., `United-Kingdom`) |

**Required secrets:** `openvpn_username`, `openvpn_password` default to empty and must be set in your inventory (ideally vault-encrypted).

The container uses the `haugene/transmission-openvpn` image which includes OpenVPN. Traffic routes through the VPN tunnel; the web UI is accessible from `transmission_openvpn_local_network` without VPN.

For a generic VPN sidecar usable with other applications (qBittorrent, SABnzbd, Prowlarr), see the `gluetun` candidate in `ROLES.md`.
