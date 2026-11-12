---
title: "Paperless-ngx"
---

Homepage: [https://github.com/paperless-ngx/paperless-ngx](https://github.com/paperless-ngx/paperless-ngx)

Paperless-ngx indexes your scanned documents and lets you search them, tag
them and store metadata alongside them. It is the maintained successor to the
archived `paperless-ng`, which it replaces in this project.

## Usage

Set `paperless_ngx_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

You also have to set `paperless_ngx_secret_key`; Paperless will not start
without it. Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Keep the key once set — changing it invalidates existing sessions and tokens.

The Paperless-ngx web interface can be found at [http://ansible_nas_host_or_ip:8110](http://ansible_nas_host_or_ip:8110).

Documents dropped into the `consume` directory under the `documents` share are
picked up and imported automatically.

## Create the superuser

The role creates a superuser on first start when both
`paperless_ngx_admin_user` and `paperless_ngx_admin_password` are set. Set them
before the first run, or leave them empty and create the user afterwards:

```bash
docker exec -it paperless-webserver python3 manage.py createsuperuser
```

This will prompt you to set a username, an optional e-mail address and finally a password (at least 8 characters).

## OCR languages

`paperless_ngx_ocr_language` is the Tesseract language used for recognition
(`eng`, or `eng+deu` for several). `paperless_ngx_ocr_languages` lists the
Tesseract language packs to install; using a language for recognition that is
not installed makes OCR fail.

## Migrating from paperless-ng

The media and consume directories have the same layout, but the database does
not: this role runs PostgreSQL 18, whereas the old `paperless_ng` role ran
PostgreSQL 13. Export from the old instance and import into the new one
instead of reusing its database volume.

1. On the old instance, export everything:

   ```bash
   docker exec -it paperless-uiserver document_exporter ../export
   ```

2. Disable `paperless_ng` and back up `{{ docker_home }}/paperless_ng`. The new
   role uses `{{ docker_home }}/paperless_ngx` and the same
   `documents/paperless` directory for media and consume, so point
   `paperless_ngx_files_directory` at the existing documents directory if it
   differs.

3. Enable `paperless_ngx`, let it start, then import:

   ```bash
   docker exec -it paperless-webserver document_importer ../export
   ```

The importer recreates documents, tags, correspondents, document types, mail
rules and saved views. The superuser is not part of the export — create it
again with `createsuperuser` and recreate any other users by hand.
