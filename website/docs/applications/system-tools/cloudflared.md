---
title: "Cloudflared"
---

Homepage: [https://github.com/cloudflare/cloudflared](https://github.com/cloudflare/cloudflared)

Cloudflare Tunnel client that publishes services without opening a port on your router. It creates an outbound-only connection to Cloudflare's edge network.

## Usage

Set `cloudflared_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Set `cloudflared_token` to the tunnel token from the Cloudflare Zero Trust dashboard (Access → Tunnels → your tunnel → Copy tunnel token).

The tunnel routes traffic to your applications via the host network, so applications must be reachable on the NAS host IP and their published ports.

## Specific Configuration

The role runs `cloudflared tunnel run --token <token>` in host networking mode. No additional ports are opened on the NAS.

If you need to route to applications on different hosts, configure the tunnel in the Cloudflare dashboard to point at the NAS host IP and the application's host port.
