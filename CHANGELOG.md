# Changelog

Breaking changes only. Image bumps, new roles and bug fixes are not listed here — they are in `git log` and in the release notes on GitHub.

A release that contains any breaking change is a major release, so a new major version means "read this file before upgrading". Releases accumulate breaks rather than shipping one per change.

## Unreleased

Nothing yet.

## v1.0.0 — 2026-11-13

First tagged release of the maintained fork of [davestephens/ansible-nas](https://github.com/davestephens/ansible-nas).

Added applications: Authelia, Cloudflared, Dozzle, Immich, Nebula Sync, Ollama, Open WebUI, Paperless-ngx, Pi-hole, Seerr, Spoolman, Tailscale, Tdarr, Uptime Kuma, WordPress, Zigbee2MQTT.

### Breaking

- `overseerr` renamed to `seerr` — set `seerr_enabled` and move your inventory overrides from `overseerr_*` to `seerr_*`; state in `{{ docker_home }}/overseerr` is not moved for you.
- `paperless_ng` renamed to `paperless_ngx` — same rename applies to its `paperless_ng_*` settings.
- Airsonic, CouchPotato, get_iplayer, Minio, pyTivo and uTorrent are not carried over — their roles were removed, so those containers stop being managed by the playbook.
