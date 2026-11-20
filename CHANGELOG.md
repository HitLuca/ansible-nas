# Changelog

Breaking changes and newly added applications. Image bumps and bug fixes are not listed here — they are in `git log` and in the release notes on GitHub.

A release that contains any breaking change is a major release, so a new major version means "read this file before upgrading". Releases accumulate breaks rather than shipping one per change.

## Unreleased

Added applications: Alloy, Audiobookshelf, Grafana, Prometheus.

### Breaking

- `stats` — role removed and split into `grafana` and `prometheus`; set `grafana_enabled` (plus a required `grafana_admin_password`) and `prometheus_enabled` instead of `stats_enabled`. The hddtemp exporter is gone (the smartctl exporter already reports disk temperature), and the unused Telegraf InfluxDB listener was removed.
- `promtail` — role removed in favour of `alloy` (promtail reached end-of-life); set `alloy_enabled` instead of `promtail_enabled`.
- `booksonic` — role removed in favour of `audiobookshelf`, so an inventory that enables it no longer deploys that container; the audio files are untouched, but users and listening progress do not carry over. See [Migrating from Booksonic](website/docs/applications/media-serving/audiobookshelf.md).
- `emby` — renamed image variables from `emby_image` + `emby_image_tag` to `emby_image_name` + `emby_image_version`; update inventory overrides accordingly.
- `heimdall` — renamed image variable from `heimdall_docker_image` to `heimdall_image_name` + `heimdall_image_version`; update inventory overrides accordingly.
- `homepage` — renamed image variable from `homepage_image_tag` to `homepage_image_version`; update inventory overrides accordingly.
- `minecraft-bedrock-server` — renamed image variable from `minecraft_bedrock_server_image` to `minecraft_bedrock_server_image_name` + `minecraft_bedrock_server_image_version`; update inventory overrides accordingly.
- `speedtest-tracker` — renamed variables from `speedtest_*` prefix to `speedtest_tracker_*` prefix (affects `speedtest_container_name`, `speedtest_data_directory`, `speedtest_image_name`, `speedtest_image_version`); update inventory overrides accordingly.
- `bitwarden` — `bitwarden_admin_token` now defaults to empty string; must be set in inventory (generate with `openssl rand -base64 48`).
- `cloudflare_ddns` — `cloudflare_ddns_token` now defaults to empty string; must be set in inventory (create at dash.cloudflare.com/profile/api-tokens).
- `drone-ci` — `drone_ci_agent_secret` and `drone_ci_gitea_client_secret` now default to empty string; must be set in inventory (generate with `openssl rand -hex 16`).
- `couchdb` — `couchdb_admin_password` now defaults to empty string; must be set in inventory.
- `immich` — `immich_db_password` and `immich_redis_password` now default to empty string; must be set in inventory.
- `joomla` — `joomla_database_password` now defaults to empty string; must be set in inventory.
- `krusader` — `krusader_vnc_password` now defaults to empty string; must be set in inventory.
- `calibre` — `calibre_password` is now required (an empty one left the Calibre desktop open to the network); set it in inventory.
- `mumble` — `mumble_server_password` now defaults to empty string; must be set in inventory.
- `miniflux` — `miniflux_admin_password` now defaults to empty string; must be set in inventory.
- `nextcloud` — `nextcloud_sql_password` and `nextcloud_sql_root_password` now default to empty string; must be set in inventory.
- `n8n` — `n8n_basic_auth_password` now defaults to empty string; must be set in inventory.
- `piwigo` — `piwigo_mysql_password` and `piwigo_mysql_root_password` now default to empty string; must be set in inventory.
- `paperless_ngx` — `paperless_ngx_db_password`, `paperless_ngx_secret_key`, and `paperless_ngx_admin_password` now default to empty string; `paperless_ngx_db_password` and `paperless_ngx_secret_key` must be set in inventory (generate with `openssl rand -hex 32`).
- `romm` — `romm_database_password`, `romm_database_root_password`, `romm_igdb_client_secret`, `romm_auth_secret_key`, and `romm_auth_password` now default to empty string; must be set in inventory (generate `romm_auth_secret_key` with `openssl rand -hex 32`).
- `silverbullet` — `silverbullet_password` now defaults to empty string; must be set in inventory.
- `timemachine` — `timemachine_password` now defaults to empty string; must be set in inventory.
- `transmission-with-openvpn` — `openvpn_password` now defaults to empty string; must be set in inventory.
- `valheim` — `valheim_password` and `valheim_set_key` now default to empty string; `valheim_password` must be set in inventory.
- `virtual_desktop` — `virtual_desktop_users[0].password` now defaults to empty string; must be set in inventory.
- `woodpecker-ci` — `woodpecker_ci_agent_secret` and `woodpecker_ci_gitea_secret` now default to empty string; must be set in inventory (generate with `openssl rand -hex 32`).
- `znc` — `znc_user_password` now defaults to empty string; must be set in inventory.
- `route53_ddns` — fixed role variable names in defaults.yml
- `cloudflare_ddns`  — fixed role variable names in defaults.yml
- `prowlarr` — moved to the official `linuxserver/prowlarr` dockerhub image, and bumped to the latest release

## v2.0.0 — 2026-11-17

Added applications: Changedetection, Dockhand, IT-Tools, Stirling PDF.

### Breaking

- `guacamole` now runs the official `guacamole/guacamole` image with its own `guacd` and PostgreSQL containers instead of `oznu/guacamole` — set `guacamole_db_password` (required, keep it once chosen); connections and users stored under `{{ guacamole_data_directory }}/config` are not migrated, so export them first and re-create them afterwards.

## v1.0.0 — 2026-11-13

First tagged release of the maintained fork of [davestephens/ansible-nas](https://github.com/davestephens/ansible-nas).

Added applications: Authelia, Cloudflared, Dozzle, Immich, Nebula Sync, Ollama, Open WebUI, Paperless-ngx, Pi-hole, Seerr, Spoolman, Tailscale, Tdarr, Uptime Kuma, WordPress, Zigbee2MQTT.

### Breaking

- `overseerr` renamed to `seerr` — set `seerr_enabled` and move your inventory overrides from `overseerr_*` to `seerr_*`; state in `{{ docker_home }}/overseerr` is not moved for you.
- `paperless_ng` renamed to `paperless_ngx` — same rename applies to its `paperless_ng_*` settings.
- Airsonic, CouchPotato, get_iplayer, Minio, pyTivo and uTorrent are not carried over — their roles were removed, so those containers stop being managed by the playbook.
