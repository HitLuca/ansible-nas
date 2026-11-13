---
title: "Authelia"
---

Homepage: [https://www.authelia.com/](https://www.authelia.com/)

Docker Container: [https://hub.docker.com/r/authelia/authelia](https://hub.docker.com/r/authelia/authelia)

Authelia is a single sign-on and two-factor authentication portal that sits in front of your applications. It is usually deployed as a Traefik forward-auth middleware, so Traefik asks Authelia whether a request is allowed before forwarding it to the application.

## Usage

Unlike most roles, Authelia needs a bit of configuration before it will start. The role refuses to run until the secrets and at least one user are set.

### Secrets

Authelia needs three secrets. Generate a separate random value for each one — never reuse a value across them, and don't reuse one you already use elsewhere.

The simplest option is Authelia's own generator, which writes the values straight to files so they stay out of your shell history and scrollback:

```bash
mkdir -p ~/authelia-secrets
docker run --rm -u "$(id -u):$(id -g)" -v ~/authelia-secrets:/out \
  authelia/authelia:4.39.28 authelia crypto rand --length 64 \
  --file /out/jwt,/out/session,/out/storage
```

That creates three `0600` files holding random alphanumeric strings. `cat` each one into your inventory, then delete the directory. `openssl rand -base64 64` is an equivalent alternative (88 characters) — quote either value in YAML.

```yaml
authelia_jwt_secret: "<contents of jwt>"
authelia_session_secret: "<contents of session>"
authelia_storage_encryption_key: "<contents of storage>"
```

Keep them in an [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) encrypted file rather than in plain `group_vars/nas.yml`:

```bash
ansible-vault create inventories/<your_inventory>/group_vars/vault.yml
```

The role refuses to start if any value is missing or too short: it requires at least 64 characters for the JWT and session secrets and 20 for the storage key, though 64 or more is recommended for all three.

The storage encryption key protects the sensitive values in `db.sqlite3`: registered TOTP secrets, WebAuthn/passkey credentials, OpenID Connect signing keys and sessions, one-time codes and bans. **Changing `authelia_storage_encryption_key` in your inventory is not enough** — the existing rows stay encrypted with the old key and Authelia will refuse to use them. Change the key in place first:

```bash
# Stop the container, then run against the existing database.
# --encryption-key is the CURRENT key, --new-encryption-key the one you want.
docker run --rm -v <authelia_data_directory>:/config authelia/authelia:4.39.28 \
  authelia storage encryption change-key \
  --config /config/configuration.yml \
  --encryption-key '<old key>' \
  --new-encryption-key '<new key>'
```

Then set the new value in your inventory and re-run the role. Verify with `authelia storage encryption check` if in doubt.

If the old key is lost, the database can't be recovered, but the loss is limited to what it encrypts: delete `db.sqlite3` and start clean. User accounts are unaffected because they live in `users_database.yml`; users have to enroll 2FA again, and OpenID Connect clients get new signing keys.

The session secret is only used with the Redis session provider, which this role does not configure: sessions are held in memory instead, so changing it just logs everyone in again when the container restarts. Use a strong random value regardless, as it becomes load-bearing if you move to Redis for high availability.

### Users

Users are rendered into `users_database.yml` from the `authelia_users` variable, keyed by username:

```yaml
authelia_users:
  alice:
    displayname: Alice
    email: alice@example.com
    groups:
      - admins
    password: "$argon2id$v=19$m=65536,t=3,p=1$..."
```

Passwords must be a hash. Generate one with the Authelia CLI:

```bash
docker run --rm authelia/authelia:4.39.28 \
  authelia crypto hash generate argon2 --password 'your-password'
```

The `Digest:` line is the value to put in `password`. A brand new database has no users, so the first user has to be added this way; afterwards users can manage their own credentials (including registering 2FA) in the portal.

See the [users database format](https://www.authelia.com/reference/guides/passwords/) for the other per-user attributes.

### Start

Set `authelia_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml`.

The portal is at [http://ansible_nas_host_or_ip:9093](http://ansible_nas_host_or_ip:9093).

Single sign-on needs Traefik (`traefik_enabled: true`) and a wildcard DNS entry for your domain — see [External Access](../../getting-started/external-access.md). The container always registers with Traefik, because the forward-auth middleware only exists while Authelia is a known proxy target. The portal is then at `https://authelia.<ansible_nas_domain>`. Without Traefik the portal still works on port 9093, but no application can delegate authentication to it.

## Protecting an application

Authelia's forward-auth middleware is defined on its own container, so any other application served through Traefik can use it. Add the middleware to that application's router in its `defaults/main.yml`:

```yaml
traefik.http.routers.<app>.middlewares: "authelia@docker"
```

For example `traefik.http.routers.nextcloud.middlewares: "authelia@docker"`.

Restart that application for the new label to take effect. The middleware is named after the container (`authelia@docker`), so it is available to any router Traefik manages as long as the Authelia role is running.

The application has to be routed through Traefik in the first place. In this repo that means setting its `<application>_available_externally` flag, which is what turns on `traefik.enable` for its container.

Which domains and paths need which policy (one factor, two factor or bypass) is controlled by the `access_control` rules in the rendered configuration. The default rule protects `*.<ansible_nas_domain>` with one factor and denies everything else.

## Configuration

The role templates `configuration.yml` and `users_database.yml` into `{{ authelia_data_directory }}` (`authelia` under your docker home) and restarts the container when they change. **Any manual edits to those two files are overwritten on the next run** — `db.sqlite3` and the rest of the directory are left alone.

The templates are a minimal, working starting point. The role's `defaults/main.yml` exposes the log level, theme and session domain; anything beyond that means editing [`roles/authelia/templates/configuration.yml.j2`](https://github.com/HitLuca/ansible-nas/blob/main/roles/authelia/templates/configuration.yml.j2) (or overriding it from your own playbook). The full option reference is at [https://www.authelia.com/configuration/prologue/introduction/](https://www.authelia.com/configuration/prologue/introduction/).

If you are coming from a hand-written `configuration.yml`, note that keys from older guides have moved in 4.39: the top-level `jwt_secret` is now `identity_validation.reset_password.jwt_secret`, and `server.host` / `server.port` are replaced by a single `server.address` in address syntax (`tcp://:9091`). Durations can also be written as `1h` / `5m` rather than a number of seconds.

Notable settings you may want to change in the template:

- `notifier` — the default writes reset notifications to `/config/notification.txt`; configure SMTP if you want password reset emails.
- `access_control` — per-domain and per-path policies.
- `identity_providers.oidc` — enable OpenID Connect for applications that support it.

If you already run Authelia elsewhere, the users database and `db.sqlite3` from your existing `CONFIG_FOLDER` can be copied into `authelia_data_directory` before the first run, as long as the secrets match.
