---
title: "Stirling PDF"
---

Homepage: [https://github.com/Stirling-Tools/Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF)

Stirling PDF is a local toolkit for working with PDFs: merge, split, rotate, compress, convert, OCR, redact and sign, all from the browser. Every file is processed on the NAS and nothing is uploaded.

## Usage

Set `stirling_pdf_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Stirling PDF web interface can be found at [http://ansible_nas_host_or_ip:8060](http://ansible_nas_host_or_ip:8060).

The role runs the interface without a login. If the port is reachable by anyone you do not trust, either put the app behind `traefik` with an `authelia` middleware or set `stirling_pdf_enable_login: true` — the first sign-in then prompts you to replace the built-in `admin` / `stirling` account.

## Data

Settings, the built-in database and anything saved from the interface live under `{{ docker_home }}/stirling_pdf`:

| Directory | Contents |
| --- | --- |
| `configs` | `settings.yml` and the internal database |
| `logs` | Application logs |
| `customFiles` | Branding overrides and saved signatures |
| `pipeline` | Watched and finished folders for automated pipelines |
| `storage` | Files saved on the server |
| `tessdata` | Extra OCR language files, copied into place on start |

## Memory

The `latest` image bundles LibreOffice, Tesseract, OCRmyPDF, Calibre, Ghostscript and ImageMagick, and the role gives it 4 GB (`stirling_pdf_memory`). A lower limit is fine for plain PDF operations but large conversions and OCR will fail when the container hits it. If you do not need Office, HTML or ebook conversion at all, the `-ultra-lite` image tag is far smaller.
