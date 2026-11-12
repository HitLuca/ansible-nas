---
title: "Tdarr"
---

Homepage: [https://tdarr.io/](https://tdarr.io/)

Docker Image: [https://github.com/HaveAGitGat/Tdarr/pkgs/container/tdarr](https://github.com/HaveAGitGat/Tdarr/pkgs/container/tdarr)

Tdarr is a distributed transcoding system for your media library. The server and
an internal node run in a single container by default; the node scans the mounted
libraries and transcodes or health-checks files according to the plugins you
configure in the web UI.

## Usage

Set `tdarr_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

Access the web UI at [http://ansible_nas_host_or_ip:8265](http://ansible_nas_host_or_ip:8265) by default.
The node server listens on port `8266`; leave that port reachable from your
network if you later add external nodes.

The `movies`, `tv`, `photos`, `music` and `downloads` shares are mounted into the
container, along with a transcode cache under `{{ docker_home }}/tdarr`. Override
any of the `tdarr_*_directory` variables to change what is mounted.

Files written by Tdarr and the node are owned by `tdarr_user_id` / `tdarr_group_id`
and created with `tdarr_umask` (default `002`).

## NVIDIA GPU transcoding

GPU transcoding is off by default. Set `tdarr_nvidia_gpu: true` to start the
container with the NVIDIA runtime and expose all GPUs:

```yaml
tdarr_nvidia_gpu: true
```

This requires the NVIDIA driver and `nvidia-container-toolkit` on the Docker host.
