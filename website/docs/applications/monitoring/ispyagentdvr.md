---
title: "iSpy Agent DVR"
---

Homepage: [https://www.ispyconnect.com/](https://www.ispyconnect.com/)

Video surveillance software with motion detection, alerts, and multi-camera support.

## Usage

Set `ispyagentdvr_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web interface is available at `http://ansible_nas_host_or_ip:8097`.

If you want to access iSpy Agent DVR externally, set `ispyagentdvr_available_externally: true`.

## Specific Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `ispyagentdvr_config_directory` | `{{ docker_home }}/ispyagentdvr/config` | Configuration storage |
| `ispyagentdvr_commands_directory` | `{{ docker_home }}/ispyagentdvr/commands` | Command scripts |
| `ispyagentdvr_recordings_directory` | `{{ downloads_root }}/recordings` | Video recordings |
| `ispyagentdvr_user_id` | `1000` | Container user ID |
| `ispyagentdvr_group_id` | `1000` | Container group ID |
| `ispyagentdvr_webui_port` | `8097` | Web UI port |
| `ispyagentdvr_turn_port` | `3478` | TURN server port |
| `ispyagentdvr_agentdvr_host_port` | `50000-50010` | Agent port range |
| `ispyagentdvr_memory` | `1g` | Memory limit |

The container runs as UID/GID 1000 by default. Ensure the configured directories are writable by that user.

Cameras are configured through the web UI after first login.
