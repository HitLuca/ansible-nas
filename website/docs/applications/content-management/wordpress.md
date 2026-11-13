---
title: "WordPress"
description: "Open source content management system, with support for hosting multiple independent sites"
---

Homepage: [https://wordpress.org](https://wordpress.org)

WordPress is a free and open source content management system (CMS) used to build websites and blogs.

This role can host **more than one website**, each with its own WordPress container, its own database and — if you want it — its own phpMyAdmin. Sites are fully independent and are stored under `websites_root` (`<shares_root>/websites` by default).

## Usage

Set `wordpress_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, then define one or more sites under `wordpress_sites`:

```yaml
wordpress_enabled: true

wordpress_sites:
  - name: myblog
    port: "9003"
    db_password: "change-me"
    db_root_password: "change-me-too"
    available_externally: true
```

Every site requires a unique `name`, a unique host `port`, and both database passwords. The site's data is written to `<shares_root>/websites/<name>/` (`wp-content` and a `db` directory).

If you want to reach a site externally through Traefik, set `available_externally: true` (globally via `wordpress_available_externally: true`, or per site). Each site is then served at `<hostname>.<your-domain>`, where `hostname` defaults to the site `name`.

Without Traefik, a site is reachable at [http://ansible_nas_host_or_ip:9003](http://ansible_nas_host_or_ip:9003) (using the site's `port`).

### Per-site settings

| Key | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | yes | — | Unique id; container/network names derive from it |
| `port` | yes | — | Unique host port for the site |
| `hostname` | no | `name` | Subdomain used by Traefik: `<hostname>.<domain>` |
| `available_externally` | no | `wordpress_available_externally` | Publish through Traefik |
| `phpmyadmin_enabled` | no | `false` | Run a dedicated phpMyAdmin for this site |
| `phpmyadmin_port` | when phpMyAdmin on | — | Unique host port for phpMyAdmin |
| `db_name` | no | `wordpress` | Database name |
| `db_user` | no | `wordpress` | Database user |
| `db_password` | yes | — | Database password |
| `db_root_password` | yes | — | Database root password |
| `memory` | no | `1g` | Memory limit for the WordPress container |
| `db_memory` | no | `1g` | Memory limit for the database container |

### phpMyAdmin (optional)

The role does not run phpMyAdmin unless a site opts in:

```yaml
wordpress_sites:
  - name: myblog
    port: "9003"
    db_password: "change-me"
    db_root_password: "change-me-too"
    phpmyadmin_enabled: true
    phpmyadmin_port: "9004"
```

phpMyAdmin is placed on the site's own network and pre-pointed at that site's database, so no manual host entry is needed.

### Reaching a site on both the port and the domain

A site is published on its host `port` and, when `available_externally` is set, also through Traefik. WordPress stores a single canonical URL (`siteurl`) in the database and redirects every request to it, so out of the box only one of the two addresses would work.

The role avoids that by defining `WP_HOME`/`WP_SITEURL` from the request's host, so the same install answers correctly at `http://nas-ip:9003` *and* at `https://<hostname>.<domain>`. This is controlled by `wordpress_config_extra_mode`:

```yaml
wordpress_config_extra_mode: "use_request_host"   # default
```

Because the role defines `WP_HOME`/`WP_SITEURL`, WordPress greys out the **Settings → General → WordPress Address / Site Address** fields: a constant wins over the database, so letting you edit them would be misleading.

The database still holds a value (`siteurl`), and WordPress shows it in those fields. It is used wherever there is no incoming request — outgoing emails, `wp-cron`, feeds and password-reset links — so set it to your primary address:

```bash
docker exec -i wordpress-<name>-db mariadb -uroot -p'<db_root_password>' wordpress \
  -e "UPDATE wp_options SET option_value='https://<hostname>.<domain>'
      WHERE option_name IN ('siteurl','home');"
```

If you would rather manage those fields in wp-admin, set:

```yaml
wordpress_config_extra_mode: "stored_siteurl"
```

The constants are then not defined, the fields become editable, and WordPress serves only on whatever address is stored in the database.

### Per-site PHP configuration

Each site can inject its own PHP into `wp-config.php` via `config_extra`, e.g. to raise the memory limit or enable debugging:

```yaml
wordpress_sites:
  - name: myblog
    port: "9003"
    config_extra: "define('WP_MEMORY_LIMIT', '512M');"
```

Changing `config_extra` recreates that site's container (the value is passed as a container environment variable).

## Specific Configuration

- The database engine is `mariadb` by default. To reuse an existing MySQL data directory (for example one created with `mysql:5.7`), override `wordpress_db_image_name: mysql` and `wordpress_db_image_version: "5.7"` — the container environment (`MYSQL_*`) and layout are compatible with the official MySQL image.
- Only `wp-content` (uploads, plugins, themes) and the database are persisted. WordPress core is provided by the image and re-created on container update, so the pinned `wordpress_image_version` determines the core version.
- The database container initialises a fresh database only when its `db` directory is empty. To migrate an existing site, copy its `wp-content` into `<shares_root>/websites/<name>/wp-content` and restore the database (e.g. with `mysqldump`).

## Migrating an existing site

1. Stop the old stack.
2. Copy the old `wp-content` into `<shares_root>/websites/<name>/wp-content`.
3. Either point the role at the old database data directory by keeping the same database image, or export it with `mysqldump` and import it into the new database container.
4. Pick a free host `port` for each site (run `make check-ports` in the repo, or simply make sure no other role uses it).
