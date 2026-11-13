---
sidebar_position: 1.5
title: "Differences from Upstream"
description: "What this fork adds compared to davestephens/ansible-nas, and how to move an existing deployment onto it"
---

Ansible-NAS is a maintained fork of [davestephens/ansible-nas](https://github.com/davestephens/ansible-nas), which is no longer actively maintained.

Roles that exist in both projects keep their name, their `<role>_*` variables, their container name and their default host port. An inventory written for upstream therefore works here unchanged, unless it configures one of the renamed or removed applications below.

## Applications this fork adds

| Application | What it does |
| --- | --- |
| [Authelia](./applications/system-tools/authelia.md) | Single sign-on and two-factor portal in front of your other applications |
| Cloudflared | Cloudflare Tunnel client, which publishes services without opening a port |
| [Dozzle](./applications/system-tools/dozzle.md) | Real-time log viewer for your running containers |
| [Immich](./applications/media-serving/immich.md) | Self-hosted photo and video library with mobile upload |
| [Nebula Sync](./applications/system-tools/nebula-sync.md) | Mirrors Pi-hole configuration between replicas |
| [Ollama](./applications/ai/ollama.md) | Runs large language models locally and serves them over an API |
| [Open WebUI](./applications/ai/open-webui.md) | Chat interface for Ollama and other LLM runtimes |
| [Paperless-ngx](./applications/other/paperless_ngx.md) | Document archive with OCR and full-text search |
| [Pi-hole](./applications/system-tools/pihole.md) | Network-wide DNS ad blocking |
| [Seerr](./applications/download-tools/seerr.md) | Media request manager for Sonarr and Radarr, successor to Overseerr |
| [Spoolman](./applications/other/spoolman.md) | Filament and spool inventory for 3D printing |
| [Tailscale](./applications/system-tools/tailscale.md) | WireGuard-based mesh VPN |
| [Tdarr](./applications/media-serving/tdarr.md) | Transcodes and health-checks your media library |
| [Uptime Kuma](./applications/monitoring/uptime-kuma.md) | Service monitor with alerting |
| [WordPress](./applications/content-management/wordpress.md) | CMS hosting one or more independent websites |
| [Zigbee2MQTT](./applications/home-automation/zigbee2mqtt.md) | Zigbee to MQTT bridge for smart home devices |

Cloudflared has no documentation page yet; its variables are declared in `roles/cloudflared/defaults/main.yml`.

## Renamed roles

Two roles were renamed to match their upstream projects. An inventory that enables them under the old name will fail with an unresolved role, so update the flag before running the playbook:

| Upstream role | This fork | Migration |
| --- | --- | --- |
| `overseerr` | `seerr` | [Migrating from the Overseerr role](./applications/download-tools/seerr.md#migrating-from-the-overseerr-role) |
| `paperless_ng` | `paperless_ngx` | [Migrating from paperless-ng](./applications/other/paperless_ngx.md#migrating-from-paperless-ng) |

## Applications not carried over

These upstream roles are not part of this fork, and `nas.yml` does not reference them:

* Airsonic
* CouchPotato
* get_iplayer
* Minio
* pyTivo
* uTorrent

If you still run one of them, keep your own copy of the role in your inventory and reference it from a playbook of your own, or stay on an earlier checkout. The rest of the fork has moved on from these applications, so the role will not receive fixes here.

## Testing and maintenance

The difference most relevant to running this on real hardware is how the roles are tested:

* **Every role has a molecule scenario.** It converges the role, runs it a second time to prove idempotence, verifies the container is running, then runs the role with its flag disabled and asserts the container is gone. The same scenario runs on Ubuntu 22.04 containers, the release this playbook targets.
* **Integration tests are scoped to the change.** CI runs the molecule scenario of the roles a pull request touches, and the full matrix once a week — which also catches upstream images that disappear or stop starting.
* **Pinned images are watched.** A weekly job reports roles whose pinned image version has fallen behind its registry (`make check-images` locally, `make update-images` to rewrite the pins within the same major version), and Renovate opens PRs for the rest. A handful of inherited roles still track a floating `latest` tag; the rest pin an explicit release.
* **Pinned images are scanned for CVEs.** Version checks only compare tags, which says nothing about what is inside a release. A second weekly job runs Trivy over every pinned image and files the fixable CRITICAL findings on a tracking issue, which summarises the affected roles and folds the per-image CVE lists away; `make scan-images` runs the same scan locally.
* **Linting is enforced, not advisory.** `ansible-lint`, `yamllint`, `markdownlint`, and scripts that check every role's enabled flag and anatomy all run on every pull request.

## Moving an existing deployment onto this fork

The data is the same either way: containers keep their names, host ports and volume paths, and nothing in the playbook touches the contents of `docker_home` or your shares. What changes is only where the code comes from. Still, take a backup of `docker_home` and your shares before you start.

1. Back up `docker_home` and your shares.

2. Point your existing checkout at this fork. Keeping the old remote means you can diff against upstream or roll back:

   ```bash
   git remote rename origin upstream
   git remote add origin https://github.com/HitLuca/ansible-nas.git
   git fetch origin
   git checkout main
   git reset --hard origin/main
   ```

   `reset --hard` discards any local change outside the inventory directory. Your inventory itself is untouched: it is not part of either repository.

3. Fix an inventory that enables a renamed or removed role, using the sections above.

4. Dry-run the whole playbook before letting it change anything:

   ```bash
   ansible-playbook -i inventories/<your-inventory>/inventory nas.yml -b -K -C
   ```

   Read the `changed` tasks. Inherited roles that were not touched should report no change. Tasks that would recreate a container are the ones worth understanding first — a changed host port or volume in a role reaches into a container you already have data in.

5. Run it for real, then re-run it once. The second run should be close to a no-op; a role that keeps reporting changes is a bug worth [an issue](https://github.com/HitLuca/ansible-nas/issues).
