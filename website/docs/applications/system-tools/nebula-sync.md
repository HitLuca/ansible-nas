---
title: "Nebula Sync"
---

Homepage: [https://github.com/lovelaze/nebula-sync](https://github.com/lovelaze/nebula-sync)

Nebula Sync keeps several Pi-hole v6 instances in sync. It copies the configuration, block lists, groups and clients from a primary Pi-hole to one or more replicas on a schedule.

## Usage

Set `nebula_sync_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, together with your Pi-hole instances. Each entry is the Pi-hole's URL and its app password, separated by `|`:

```yaml
nebula_sync_enabled: true
nebula_sync_primary: "http://192.168.1.2|primary-app-password"
nebula_sync_replicas:
  - "http://192.168.1.3|replica-app-password"
```

These are admin credentials for your Pi-holes, so keep them in an [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) encrypted file.

By default the role runs a full sync every night at midnight and then updates gravity on the replicas. Settings you can change:

- `nebula_sync_cron`: cron schedule, default `"0 0 * * *"`. An empty value runs one sync and exits.
- `nebula_sync_full_sync`: `true` copies everything. Set it to `false` to sync only the sections you enable through `nebula_sync_extra_env`.
- `nebula_sync_run_gravity`: update gravity on the replicas after each sync.
- `nebula_sync_skip_tls_verification`: accept self-signed HTTPS certificates on the Pi-holes.
- `nebula_sync_extra_env`: any other [nebula-sync setting](https://github.com/lovelaze/nebula-sync#configuration), for example:

```yaml
nebula_sync_full_sync: false
nebula_sync_extra_env:
  SYNC_CONFIG_DNS: "true"
  SYNC_GRAVITY_AD_LIST: "true"
  SYNC_GRAVITY_DOMAIN_LIST: "true"
```

Nebula Sync has no web interface. Check `docker logs nebula-sync` to see the result of each sync.
