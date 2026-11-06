---
title: "Zigbee2MQTT"
---

Homepage: [https://www.zigbee2mqtt.io](https://www.zigbee2mqtt.io)

Docker Container: [https://hub.docker.com/r/koenkk/zigbee2mqtt](https://hub.docker.com/r/koenkk/zigbee2mqtt)

Zigbee2MQTT lets you use Zigbee devices without the vendor's bridge or gateway. It talks to a Zigbee USB adapter and publishes device state over MQTT, where Home Assistant, openHAB, n8n and others can pick it up.

## Usage

Set `zigbee2mqtt_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, and point `zigbee2mqtt_device_path` at your Zigbee adapter:

```yaml
zigbee2mqtt_enabled: true
zigbee2mqtt_device_path: "/dev/serial/by-id/usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_..."
```

Run `ls -l /dev/serial/by-id/` on the NAS to find it. The `by-id` path stays the same across reboots, unlike `/dev/ttyACM0` or `/dev/ttyUSB0`. Inside the container the adapter is always available as `/dev/ttyACM0`.

Zigbee2MQTT needs an MQTT broker. You can run one on the NAS with the [Mosquitto](mosquitto.md) role.

The web interface can be found at [http://ansible_nas_host_or_ip:8080](http://ansible_nas_host_or_ip:8080). On a fresh install it opens the onboarding page, where you set the adapter (`/dev/ttyACM0`) and the MQTT server. Configuration is stored in `zigbee2mqtt/data/configuration.yaml` under your docker home.

Change `zigbee2mqtt_port` if 8080 is already taken on your NAS.

## Security

The web interface has no login by default. If you set `zigbee2mqtt_available_externally: true`, first set `frontend.auth_token` in `configuration.yaml`.
