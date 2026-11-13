---
title: "Guacamole"
---

Homepage: [https://guacamole.apache.org/](https://guacamole.apache.org/)

Apache Guacamole is a clientless remote desktop gateway. It supports standard protocols like VNC, RDP, and SSH.

## Usage

Set `guacamole_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file, and set `guacamole_db_password` to a long random string.

The role runs three containers: `guacamole` (the web application), `guacamole-guacd` (the protocol proxy) and `guacamole-postgres` (the database). Guacamole does not create its own schema, so the role initializes the database on first start.

## Specific Configuration

The default username and password is `guacadmin`. Change it!

Changing `guacamole_db_password` after the first start locks Guacamole out of its own database, because PostgreSQL only uses that value when it initializes the data directory.

## What to connect to?

You can run a virtual desktop from your Ansible-NAS box, check out the [Virtual Desktop docs](virtual_desktop.md).

## Migrating from the old `oznu/guacamole` image

Earlier versions of this role used the archived `oznu/guacamole` image, which kept its PostgreSQL database inside `<docker_home>/guacamole/config`. Deploying this version replaces that container, so export the data first.

Before running the playbook, with the old container still running:

```shell
ssh <nas>
docker exec guacamole pg_dump -U guacamole -d guacamole_db --no-owner > guacamole-old.sql
```

Then enable the role with a `guacamole_db_password` set and run the playbook. Once the new containers are up, load the old data over the freshly created schema and apply the one schema upgrade that Guacamole 1.3.0 needs to work with 1.6.0:

```shell
ssh <nas>
docker exec guacamole-postgres psql -U guacamole -d guacamole_db \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
docker exec -i guacamole-postgres psql -U guacamole -d guacamole_db < guacamole-old.sql
curl -O https://raw.githubusercontent.com/apache/guacamole-client/1.6.0/extensions/guacamole-auth-jdbc/modules/guacamole-auth-jdbc-postgresql/schema/upgrade/upgrade-pre-1.6.0.sql
docker exec -i guacamole-postgres psql -U guacamole -d guacamole_db < upgrade-pre-1.6.0.sql
docker restart guacamole
```

Your users and connections are then available as before. The role leaves the old `config` directory untouched; remove it once you are happy with the new install.
