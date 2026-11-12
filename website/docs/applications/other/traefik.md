---
title: "Traefik"
---

Homepage: [https://traefik.io](https://traefik.io)

Traefik is a reverse proxy used to provide external access to your Ansible-NAS box. Additionally, Traefik will automatically request and renew SSL certificates for you.

You can configure which applications are available externally by enabling the `<application_name>_available_externally` setting
for each application in the Advanced Settings section of your `all.yml`.

See [External Access](../../getting-started/external-access.md) for more info.

## Usage

Set `traefik_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Traefik's web interface can be found at [http://ansible_nas_host_or_ip:8083](http://ansible_nas_host_or_ip:8083).

## Specific Configuration

You'll need to map port 80 and 443 from your router to your Ansible-NAS box. A quick search should reveal instruction for your model of router.

## Routing to services that aren't containers

Traefik picks up routers from Docker labels, so applications installed by Ansible-NAS are exposed automatically. For a backend that isn't a container on the NAS — another machine on your LAN, for example — declare the router and service yourself:

```yaml
traefik_dynamic_config_extra:
  http:
    routers:
      printer:
        entryPoints:
          - https
        service: printer
        rule: "Host(`printer.{{ ansible_nas_domain }}`)"
        tls:
          certResolver: letsencrypt
    services:
      printer:
        loadBalancer:
          servers:
            - url: http://printer/
```

This is deep-merged into the file provider's `dynamic_config.yml`, so the TLS options stay as they are. Put it in `host_vars/<host>.yml` so each NAS only routes to the machines it can reach, and make sure any middleware you reference (`authelia@docker`, for example) is enabled on that host.
