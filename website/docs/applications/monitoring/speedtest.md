---
title: "Speedtest-Tracker"
---

Homepage: [https://github.com/alexjustesen/speedtest-tracker](https://github.com/alexjustesen/speedtest-tracker)

Docker Container: [https://github.com/linuxserver/docker-speedtest-tracker](https://github.com/linuxserver/docker-speedtest-tracker)

Continuously track your internet speed

## Usage

Set `speedtest_tracker_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Speedtest-Tracker needs an app key to encrypt its stored data. Generate one once and set it as `speedtest_tracker_app_key` in the same file (ideally vault-encrypted):

```bash
echo "base64:$(openssl rand -base64 32)"
```

Tests run every 6 hours by default; change `speedtest_tracker_schedule` (cron format) to adjust.

If you want to access Speedtest-Tracker externally, don't forget to set `speedtest_tracker_available_externally: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, and set `speedtest_tracker_app_url` to the external URL.

The Speedtest-Tracker interface can be found at [http://ansible_nas_host_or_ip:8765](http://ansible_nas_host_or_ip:8765).

## Upgrading from the old Speedtest-Tracker

Earlier versions of this role used the abandoned `henrywhitaker3/speedtest-tracker` image. The maintained version is a rewrite, and its data isn't compatible. It starts with an empty history in `speedtest_tracker/data`. The old data stays in `speedtest_tracker/config`, and you can delete it once you no longer need it.
