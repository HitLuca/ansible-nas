---
title: "Pi-hole"
---

Homepage: [https://pi-hole.net/](https://pi-hole.net/)

Docker Container: [https://hub.docker.com/r/pihole/pihole](https://hub.docker.com/r/pihole/pihole)

Pi-hole is a DNS sinkhole: point your router (or individual clients) at the NAS
for DNS and it blocks ad and tracker domains network-wide, with a dashboard
showing what it filtered.

## Usage

Set `pihole_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The admin interface is then reachable at `http://ansible_nas_host_or_ip:8072/admin`.
The web root itself answers 404, so `pihole_web_path` (default `/admin`) is what
the Homepage link and the Uptime Kuma monitor use.

### Admin password

By default no password is set, so Pi-hole generates a random one on first start
and prints it in the container log:

```bash
docker logs pihole
```

Set `pihole_web_password` to pin your own instead. Changing it later through the
web UI works too, but recreating the container with this variable still empty
will not overwrite a password you already set in the UI.

### Pointing clients at Pi-hole

DNS is published on the NAS host address at `pihole_dns_port` (53 by default),
over both TCP and UDP. Configure your router's DHCP server to hand out the NAS
address as the DNS server, or set it per device.

`pihole_dns_bind_address` defaults to `pihole_host_ip`, so DNS is published on
one address rather than every interface. Set it to `0.0.0.0` if clients reach
the NAS on an address other than the one Ansible detects.

The same host port can only be claimed once. If another DNS resolver already
listens on 53 — `adguardhome`, a system `dnsmasq`, or `systemd-resolved` bound to
all interfaces — move this role's DNS to another port or stop the other
resolver.

`FTLCONF_LOCAL_IPV4` is set to `pihole_host_ip`, and Pi-hole answers DNS
queries with that address. Set `pihole_host_ip` to the address clients actually
see, or the generated records will point at the wrong host.

### Upstream resolvers

Pi-hole forwards unblocked queries to its configured upstreams. Set them in the
web UI under *Settings → DNS*; the choice is stored in the `etc-pihole` volume
and survives container re-creation.

## Specific Configuration

The role deliberately does **not** enable Pi-hole as a DHCP server. DHCP needs
port 67, `NET_ADMIN`, and (usually) host networking, none of which are set here;
keep serving DHCP from your router.

Exposing the admin UI through Traefik with `pihole_available_externally: true`
works, but the DNS service itself is unaffected by that flag and is always
published on the host port above.
