---
title: "Uptime Kuma"
---

Homepage: [https://github.com/louislam/uptime-kuma](https://github.com/louislam/uptime-kuma)

Self-hosted uptime monitoring tool with status pages and notifications.

## Usage

Set `uptime_kuma_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Uptime Kuma web interface can be found at [http://ansible_nas_host_or_ip:3003](http://ansible_nas_host_or_ip:3003).

If you want to access Uptime Kuma externally, don't forget to set `uptime_kuma_available_externally: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

## Specific Configuration

The first visit asks you to create an admin account. All data, including monitors and notification settings, is stored in `uptime_kuma_data_directory`.

## Automatic monitor discovery

Uptime Kuma has no public API for creating monitors — its REST endpoints are read-only plus push reporting. The role therefore ships [AutoKuma](https://github.com/BigBoot/AutoKuma), a sidecar container that watches Docker labels and creates or updates the matching monitors. It talks to Uptime Kuma's internal Socket.IO API, which upstream does not support as a stable interface, so treat monitor creation as best-effort.

Discovery is off by default. To turn it on, first create your account in the Uptime Kuma web UI, then set in `inventories/<your_inventory>/group_vars/nas.yml`:

```yaml
uptime_kuma_discovery_enabled: true
uptime_kuma_discovery_username: <your Uptime Kuma username>
uptime_kuma_discovery_password: <your Uptime Kuma password>
```

Then pick what gets monitored. Either every role that exposes a web UI:

```yaml
uptime_kuma_monitor_all_services: true
```

or individual roles, leaving the rest alone:

```yaml
sonarr_uptime_kuma_monitor: true
jellyfin_uptime_kuma_monitor: true
```

Each application is checked at `http://<nas>:<application port>`, which bypasses Traefik and Authelia, so the monitor keeps working when the proxy is down. Monitors check every 5 minutes with two retries. Roles without a web UI (MQTT brokers, game servers, log shippers) never get a monitor.

### Notes

- AutoKuma mounts the Docker socket read-only and keeps its state in `uptime_kuma_discovery_data_directory`. If that directory is lost, AutoKuma no longer recognises the monitors it made and cannot delete them.
- The sidecar is pinned to AutoKuma 2.1.0-rc.2 because 2.0.0 never reconnects: after the Uptime Kuma connection dropped (a Uptime Kuma restart is enough), it kept using the dead socket and stopped syncing for good, stranding monitors for containers that no longer existed. On 2.0.0 the only fix was restarting `uptime-kuma-discovery` itself.
- Disabling an application makes the playbook delete its container (the role's stop block uses `state: absent`), and AutoKuma drops the monitor a minute later.
- Stopping a container is **not** enough. AutoKuma lists containers including stopped ones, so `docker stop <container_name>` leaves the monitor in place, where it shows as down. Remove the container (`docker rm -f <container_name>`, or run the playbook with that role's flag off) to have the monitor deleted.
- AutoKuma only deletes monitors it created and still tracks in its state directory. A monitor left over from an earlier AutoKuma install, or one created by hand in the UI, is never touched — delete it once in the UI, after which the role keeps everything in sync.
- Turning off `uptime_kuma_monitor_all_services`, or a single `<role>_uptime_kuma_monitor`, while its container keeps running leaves the existing monitor in place: Docker cannot drop a label from a live container. Remove the container (`docker rm -f <container_name>`) and re-run the playbook to have the labels dropped, or delete the monitor in the UI.
- Uptime Kuma can't reliably monitor itself — when it is down, so are its alerts. Use a separate checker such as the [healthchecks.io](../system-tools/healthchecks.io.md) role for that.
