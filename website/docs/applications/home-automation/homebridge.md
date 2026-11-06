---
title: "Homebridge"
---

Homepage: [https://homebridge.io](https://homebridge.io)

Docker Container: [https://github.com/homebridge/docker-homebridge](https://github.com/homebridge/docker-homebridge)

Homebridge is a lightweight NodeJS server you can run on your home network that emulates the iOS HomeKit API. It supports Plugins, which are community-contributed modules that provide a basic bridge from HomeKit to various 3rd-party APIs provided by manufacturers of "smart home" devices.

## Usage

Set `homebridge_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Homebridge web interface can be found at [http://ansible_nas_host_or_ip:8581](http://ansible_nas_host_or_ip:8581). On a fresh install, follow the first-run setup in the UI to create your login.

## Upgrading from the oznu/homebridge image

Earlier versions of this role used the deprecated `oznu/homebridge` image with the UI on port 8087. The UI port is stored in `config.json` inside `homebridge/config`, so an existing install keeps using 8087 after the switch. Set `homebridge_port: "8087"` in your inventory so the Traefik route matches, or change the port in the Homebridge UI settings to 8581.
