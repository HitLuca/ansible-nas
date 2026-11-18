# Changelog

Breaking changes and newly added applications. Image bumps and bug fixes are not listed here — they are in `git log` and in the release notes on GitHub.

A release that contains any breaking change is a major release, so a new major version means "read this file before upgrading". Releases accumulate breaks rather than shipping one per change.

## Unreleased

Added applications: Alloy, Audiobookshelf, Grafana, Prometheus.

### Breaking

- `stats` — role removed and split into `grafana` and `prometheus`; set `grafana_enabled` (plus a required `grafana_admin_password`) and `prometheus_enabled` instead of `stats_enabled`. The hddtemp exporter is gone (the smartctl exporter already reports disk temperature), and the unused Telegraf InfluxDB listener was removed.
- `promtail` — role removed in favour of `alloy` (promtail reached end-of-life); set `alloy_enabled` instead of `promtail_enabled`.
- `booksonic` — role removed in favour of `audiobookshelf`, so an inventory that enables it no longer deploys that container; the audio files are untouched, but users and listening progress do not carry over. See [Migrating from Booksonic](website/docs/applications/media-serving/audiobookshelf.md).

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
