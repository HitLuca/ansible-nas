---
title: "Open WebUI"
---

Homepage: [https://openwebui.com](https://openwebui.com)

Open WebUI is a self-hosted, ChatGPT-style chat interface for Ollama and other
OpenAI-compatible language model runtimes.

## Usage

Set `open_webui_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Open WebUI also requires a secret key, which signs sessions and encrypts stored
settings. Generate one, keep it (changing it invalidates existing logins), and
set it:

```bash
openssl rand -base64 32
```

```yaml
open_webui_enabled: true
open_webui_secret_key: "<the generated value>"
```

The web interface can be found at [http://ansible_nas_host_or_ip:8098](http://ansible_nas_host_or_ip:8098).

## Connecting to Ollama

By default Open WebUI talks to the [`ollama`](./ollama.md) role on the host
at `http://<nas-ip>:11434`, so enabling `ollama_enabled: true` is enough — the
two roles do not share a Docker network and either can run alone.

To use an Ollama server on a different machine, override the endpoint:

```yaml
open_webui_ollama_base_url: "http://10.0.0.5:11434"
```

## Specific Configuration

- `open_webui_data_directory` holds the SQLite database, uploaded files and
  settings. Back it up to keep chats and users.
- `open_webui_memory` (default `2g`) caps the container's memory.
