---
title: "Tailscale"
---

Homepage: [https://tailscale.com](https://tailscale.com)

Docker Container: [https://hub.docker.com/r/tailscale/tailscale](https://hub.docker.com/r/tailscale/tailscale)

Tailscale is a mesh VPN built on WireGuard. It lets your devices reach the NAS from anywhere without opening ports on your router. With subnet routes it can also reach the rest of your home network.

## Usage

Set `tailscale_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The container uses the host network, so the NAS itself joins your tailnet under the name `tailscale_hostname` (defaults to `ansible_nas_hostname`). All services on the NAS are then reachable on its Tailscale IP or MagicDNS name.

### Logging in

You can log in in either of two ways:

- Set `tailscale_auth_key` to an auth key from the [admin console](https://login.tailscale.com/admin/settings/keys). Keep it in an Ansible Vault encrypted file.
- Leave it empty, run `docker logs tailscale` after the first start, and open the login URL it prints.

The login is kept in `tailscale_data_directory`, so you only need to do this once.

### Subnet routes and exit node

To reach other devices on your home network through the NAS, list the subnets to advertise:

```yaml
tailscale_routes: "192.168.1.0/24"
```

To use the NAS as an exit node:

```yaml
tailscale_extra_args: "--advertise-exit-node"
```

In both cases the role turns on IP forwarding on the host. You then need to approve the routes or the exit node under the machine's "Edit route settings" in the Tailscale admin console.

## Moving from a docker compose / Portainer setup

If you ran Tailscale with `/var/lib` mounted from a config folder, the node state is in the `tailscale` subfolder of that folder. Copy that subfolder's contents into `tailscale_data_directory` (by default `tailscale` under your docker home) before the first run, and the NAS keeps its existing identity and IP in your tailnet.
