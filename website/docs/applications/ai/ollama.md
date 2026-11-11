---
title: "Ollama"
---

Homepage: [https://ollama.com](https://ollama.com)

Ollama runs large language models locally and serves them over an HTTP API on
port 11434. Pair it with [Open WebUI](./open-webui.md) for a chat interface, or
point any Ollama-compatible client at it.

## Usage

Set `ollama_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The API is then reachable at `http://ansible_nas_host_or_ip:11434`:

```bash
curl http://ansible_nas_host_or_ip:11434/api/tags
```

Models are pulled into the `ollama_data_directory` volume, so they survive
container restarts:

```bash
docker exec ollama ollama pull llama3.2
```

## NVIDIA GPU

Ollama uses the CPU by default. Set `ollama_nvidia_gpu: true` to pass through
the first NVIDIA GPU, which requires the NVIDIA driver and the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
on the host:

```yaml
ollama_nvidia_gpu: true
```

Check that the GPU is visible with `docker exec ollama nvidia-smi`.

## Exposing the API

There is deliberately no `ollama_available_externally` flag. The API has no
authentication, so publishing it through Traefik would expose an unauthenticated
endpoint to the internet. Reach it over a VPN or SSH tunnel instead, or put an
authenticating reverse proxy in front of it.

## Specific Configuration

`ollama_memory` (default `8g`) caps the container's memory. Models are loaded
into RAM while in use, so raise it for larger models — a model that does not fit
runs far slower than one that does.
