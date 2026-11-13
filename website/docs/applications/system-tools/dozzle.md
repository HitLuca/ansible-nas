---
title: "Dozzle"
---

Homepage: [https://dozzle.dev/](https://dozzle.dev/)

Docker Container: [https://hub.docker.com/r/amir20/dozzle](https://hub.docker.com/r/amir20/dozzle)

Real-time log viewer for your Docker containers, in the browser

## Usage

Set `dozzle_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Dozzle web interface can be found at [http://ansible_nas_host_or_ip:8888](http://ansible_nas_host_or_ip:8888).

Dozzle reads the logs of every container on the host, so anyone who can reach it can see everything your containers print. To require a login, set `dozzle_auth_provider: "simple"` and list users under `dozzle_users`:

```yaml
dozzle_auth_provider: "simple"
dozzle_users:
  admin:
    name: Admin
    email: me@example.com
    password: "$2a$11$..."
```

Passwords must be bcrypt hashes. Generate the entry with:

```bash
docker run -it --rm amir20/dozzle:v11.4.2 generate admin --name Admin --email me@example.com
```

Dozzle prompts for the password, so it stays out of your shell history, then prints a `users.yml` block. Copy its `name`, `email` and `password` values into `dozzle_users`.

To limit what a user can see or do, pass `--user-filter` and `--user-roles` to the generator and copy the resulting `filter` and `roles` values too. Both are comma-separated strings; a user without `roles` gets full access.

Logins last 24 hours by default; change `dozzle_auth_ttl` (units `s`, `m` and `h`) to adjust.

If you want to access Dozzle externally, don't forget to set `dozzle_available_externally: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.
