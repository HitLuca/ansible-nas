---
title: "Immich"
---

Homepage: [https://immich.app/](https://immich.app/)

Immich is a self-hosted photo and video backup solution. This role runs the ImageGenius all-in-one image (server and machine learning in one container) with separate PostgreSQL and Valkey containers, so the database and cache can live on their own volumes.

## Usage

Set `immich_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Immich web interface can be found at [http://ansible_nas_host_or_ip:8039](http://ansible_nas_host_or_ip:8039).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `immich_port` | `8039` | Host port for the web interface. |
| `immich_photos_directory` | `{{ photos_root }}` | Main upload library, mounted at `/photos`. |
| `immich_libraries` | `[]` | Extra bind mounts in `host:container[:mode]` form, e.g. `"/mnt/photos/user:/libraries/user:ro"`. |
| `immich_user_id` / `immich_group_id` | `1000` | PUID/PGID the container writes as. Must match the ownership of the existing data. |
| `immich_db_storage_type` | `HDD` | `HDD` or `SSD`; tunes the PostgreSQL I/O profile. |
| `immich_db_password` | `postgres` | Password used by both PostgreSQL and Immich. Only reachable on the internal Docker network. |
| `immich_nvidia_gpu` | `false` | Run with the NVIDIA container runtime and expose all GPUs. |
| `immich_image_version` | `3.4.0` | Use `3.4.0-cuda` when `immich_nvidia_gpu` is enabled. |
| `immich_memory` / `immich_postgres_memory` / `immich_valkey_memory` | `6g` / `2g` / `1g` | Container memory limits. Raise them if Immich or the database gets OOM-killed on a large library. |

The PostgreSQL data directory is `immich_postgres_directory` (`{{ docker_home }}/immich/postgres_data` by default). The role defaults the PostgreSQL image to the same PostgreSQL 14 + VectorChord 0.3.0 image Immich ships with, so the on-disk database format is not changed.

## Hardware acceleration

NVIDIA CUDA acceleration needs the [NVIDIA container toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed on the host. Then set:

```yaml
immich_nvidia_gpu: true
immich_image_version: "3.4.0-cuda"
```

The role passes `--runtime=nvidia` and sets `NVIDIA_VISIBLE_DEVICES=all` and `NVIDIA_DRIVER_CAPABILITIES=compute,video,utility`. Leave both settings at their defaults to run machine learning on the CPU.

`3.4.0` and `3.4.0-cuda` are the same Immich version — only the machine-learning runtime differs. Deploying the CPU variant on a machine with a GPU costs inference speed, not data, so a wrong guess here is recoverable.

## Existing libraries

Files placed in `immich_photos_directory` are visible as `/photos` inside the container. To track libraries that live elsewhere, add one entry per host folder:

```yaml
immich_libraries:
  - "/mnt/Volume3/photos/user1:/libraries/user1:ro"
  - "/mnt/Volume3/photos/user2:/libraries/user2:ro"
```

Register the matching container paths in Immich's administration settings, then add them as external libraries in each user's account settings.

## Migrating an existing Immich stack

The role can take over containers that were previously managed by Portainer or a hand-written Compose file. Disabling or re-running the role only removes the **containers**; every path in `immich_config_directory`, `immich_postgres_directory`, `immich_photos_directory` and `immich_libraries` is a bind mount, so the data stays on disk.

Before switching over:

1. Read the exact host paths the old stack used, instead of guessing them:

   ```bash
   docker inspect immich \
     --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
   ```

2. Confirm the running image is the version the role pins. The image ID Docker reports is the registry's config digest, so the two are directly comparable:

   ```bash
   docker inspect --format '{{.Image}}' immich
   curl -s http://nas:8085/api/server/version
   ```

   If the running image is older than `immich_image_version`, set `immich_image_version` to the matching pinned tag for the version you run now, and upgrade separately after a backup. Immich migrations run on startup and are forward-only. If the old stack used the floating `cuda` tag, it resolved to `3.4.0-cuda`: set `immich_image_version: "3.4.0-cuda"` and `immich_nvidia_gpu: true`.

3. **Back up** the database. The data directory is a bind mount, so there is no Docker volume to copy — dump the database itself:

   ```bash
   docker exec immich-postgres pg_dumpall --clean --if-exists --username=postgres \
     > immich-db.sql
   ```

   Stopping a container is safe, but never delete the bind-mounted directories while the stack is in use.

4. Stop and remove the old stack's **containers** with its own tool (`docker compose rm -sf`, Portainer's remove button with volumes left untouched). Do not run `down -v`, and do not delete the bind-mounted directories.
5. Point the role at the exact directories the old stack bind-mounted (the paths from step 1):

   ```yaml
   # Substitute the values your Compose file read from ${CONFIG_FOLDER},
   # ${PHOTOS_FOLDER}, ${USER1_PHOTOS_FOLDER}, ...
   immich_config_directory: "{{ docker_home }}/immich/config"
   immich_postgres_directory: "{{ docker_home }}/immich/postgres_data"
   immich_photos_directory: "/mnt/Volume3/photos"

   immich_libraries:
     - "/mnt/Volume3/photos/user1:/libraries/user1"
     - "/mnt/Volume3/photos/user2:/libraries/user2"
     - "/mnt/Volume3/photos/user3:/libraries/user3"
   ```

   If the old `${CONFIG_FOLDER}` was `{{ docker_home }}/immich`, the first two defaults already match and only the photo paths need setting.
6. Set `immich_user_id` and `immich_group_id` to the PUID/PGID the old stack used. Check the owner of the existing files with `ls -ln`; the container cannot write if these do not match.
7. Keep `immich_db_username`, `immich_db_password` and `immich_db_name` on the values the existing PostgreSQL volume was initialised with.
8. Keep the PostgreSQL image pin. Changing `immich_postgres_image_version` points the container at a different database image and can make the existing data directory unreadable.

The role does not publish PostgreSQL (5432) or Valkey (6379) on the host; Immich reaches both over the private `immich` Docker network. If something else was connecting to those ports on the old stack, leave it in place and adjust the role instead of switching over.

Then deploy only this role:

```bash
ansible-playbook nas.yml --tags immich
```

The old host port is not preserved by default. If something links directly to `http://nas:8085`, set `immich_port: "8085"` — after checking that no other enabled role uses that port (`make check-ports` reports default collisions).
