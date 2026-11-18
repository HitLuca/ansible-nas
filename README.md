<h1 align="center"><img src="website/static/img/ansible-nas-logo.png" alt="Ansible-NAS logo" width="200"><br>Ansible NAS</h1>

<div align="center">

<p><b>Turn a stock Ubuntu box into a self-hosted home server — one Ansible role per application, deployed as Docker containers.</b></p>

<p><a href="https://hitluca.github.io/ansible-nas/">Docs</a> · <a href="#available-applications">Applications</a> · <a href="https://hitluca.github.io/ansible-nas/docs/getting-started/installation/">Installation</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

![applications](https://img.shields.io/github/directory-file-count/HitLuca/ansible-nas/roles?label=applications&style=flat-square) [![CI](https://img.shields.io/github/actions/workflow/status/HitLuca/ansible-nas/ci.yml?label=CI&style=flat-square)](https://github.com/HitLuca/ansible-nas/actions/workflows/ci.yml) [![integration](https://img.shields.io/github/actions/workflow/status/HitLuca/ansible-nas/integration.yml?label=integration&style=flat-square)](https://github.com/HitLuca/ansible-nas/actions/workflows/integration.yml) [![CodeQL](https://img.shields.io/github/actions/workflow/status/HitLuca/ansible-nas/codeql.yml?label=CodeQL&style=flat-square)](https://github.com/HitLuca/ansible-nas/actions/workflows/codeql.yml)<br>
[![release](https://img.shields.io/github/v/release/HitLuca/ansible-nas?style=flat-square)](https://github.com/HitLuca/ansible-nas/releases) ![last commit](https://img.shields.io/github/last-commit/HitLuca/ansible-nas?style=flat-square) ![Ubuntu 22.04 LTS](https://img.shields.io/badge/ubuntu-22.04%20LTS-E95420?style=flat-square) [![license](https://img.shields.io/github/license/HitLuca/ansible-nas.svg?style=flat-square)](LICENSE)

</div>

> [!NOTE]
> This is a maintained fork of [davestephens/ansible-nas](https://github.com/davestephens/ansible-nas), which is no longer actively maintained. All credit for the original project goes to David Stephens and its contributors.
>
> See [Differences from Upstream](https://hitluca.github.io/ansible-nas/docs/differences-from-upstream) for the applications this fork adds, the roles it renamed or dropped, and how to move an existing deployment onto it.

After getting burned by broken FreeNAS updates one too many times, I figured I could do a much better job myself using just a stock Ubuntu install, some clever Ansible config and a bunch of Docker containers.

## Highlights

* 🧩 **One role per application** — enable any (or all!) of the applications below with a single flag.
* 🌐 **External access** — with a spare domain, applications get a sensible hostname, Traefik with Let's Encrypt, and DNS that follows your home IP.
* 🔐 **Optional SSO** — put [Authelia](https://hitluca.github.io/ansible-nas/docs/applications/system-tools/authelia) in front of anything you expose.
* ✅ **Tested** — every role has a Molecule scenario in CI, with pinned image versions and a weekly integration run.

## Quick Start

```bash
git clone https://github.com/HitLuca/ansible-nas.git && cd ansible-nas
# create your inventory and enable the applications you want, then:
ansible-playbook -i inventories/<your-inventory> nas.yml -b -K
```

The [installation guide](https://hitluca.github.io/ansible-nas/docs/getting-started/installation/) covers the inventory, required variables and first run.

## Requirements

* Ansible NAS is built and tested on Ubuntu Server 22.04 LTS. That is the supported release: newer LTS versions have not been tested and are unsupported for now.
* You can run Ansible-NAS on whatever hardware you like, read the docs for more info.

## Available Applications

Ansible-NAS deploys any (or all) of the applications below. They are grouped the same way as the [documentation](https://hitluca.github.io/ansible-nas/docs/applications/), which has the configuration details for each one.

<details>
<summary><b>AI</b> (2)</summary>

| Application | Description |
| --- | --- |
| [Ollama](https://ollama.com/) | Run large language models locally and serve them over an API |
| [Open WebUI](https://openwebui.com/) | Self-hosted chat interface for Ollama and other LLM runtimes |

</details>

<details>
<summary><b>Content Management</b> (4)</summary>

| Application | Description |
| --- | --- |
| [DokuWiki](https://www.dokuwiki.org/) | Simple, highly versatile open source wiki software that doesn't require a database |
| [Joomla](https://www.joomla.org/) | Open source content management system |
| [TiddlyWiki](https://tiddlywiki.com) | Non-linear notebook for capturing, organising and sharing complex information |
| [WordPress](https://wordpress.org/) | Open source content management system, with support for hosting multiple independent sites |

</details>

<details>
<summary><b>Dashboards</b> (4)</summary>

| Application | Description |
| --- | --- |
| [Dashy](https://dashy.to/) | Self-hosted startpage with a visual editor, status checking, widgets and themes |
| [Heimdall](https://heimdall.site/) | Home server dashboard |
| [Homepage](https://gethomepage.dev/) | Highly customisable application dashboard with integrations for over 100 services |
| [Organizr](https://organizr.app/) | One-stop shop for your server frontend |

</details>

<details>
<summary><b>Development Tools</b> (7)</summary>

| Application | Description |
| --- | --- |
| [Code Server](https://code.visualstudio.com/) | VS Code IDE in the browser |
| [Drone CI](https://drone.io) | Self-service continuous integration platform |
| [Gitea](https://gitea.io/en-us/) | Simple self-hosted GitHub clone |
| [GitLab](https://about.gitlab.com/features/) | Full-featured self-hosted GitHub clone |
| [IT-Tools](https://it-tools.tech/) | Collection of handy online tools for developers |
| [Nomad](https://www.nomadproject.io/) | Simple and flexible scheduler and software orchestrator |
| [Woodpecker-CI](https://woodpecker-ci.org) | Simple CI engine with great extensibility, forked from Drone |

</details>

<details>
<summary><b>Download Tools</b> (17)</summary>

| Application | Description |
| --- | --- |
| [Bazarr](https://github.com/morpheus65535/bazarr) | Companion to Radarr and Sonarr for downloading subtitles |
| [Deluge](https://dev.deluge-torrent.org/) | Lightweight, cross-platform BitTorrent client |
| [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | Proxy server to bypass Cloudflare and DDoS-GUARD protection |
| [Jackett](https://github.com/Jackett/Jackett) | API support for your favourite torrent trackers |
| [Lidarr](https://github.com/lidarr/Lidarr) | Music collection manager for Usenet and BitTorrent users |
| [Mylar](https://github.com/evilhero/mylar) | Automated comic book downloader (cbr/cbz) for SABnzbd, NZBGet and torrents |
| [NZBget](https://nzbget.net/) | Efficient usenet downloader |
| [Ombi](https://ombi.io/) | Gives your users the ability to request content automatically |
| [Prowlarr](https://github.com/Prowlarr/Prowlarr) | Indexer aggregator for Sonarr, Radarr, Lidarr and friends |
| [pyLoad](https://pyload.net/) | Download manager with a friendly web interface |
| [Radarr](https://radarr.video/) | For organising and downloading movies |
| [Sabnzbd](https://sabnzbd.org/) | Powerful usenet downloader |
| [Seerr](https://docs.seerr.dev) | Manages requests for your media library (successor of Overseerr) |
| [Sickchill](https://sickchill.github.io/) | For managing TV episodes |
| [Sonarr](https://sonarr.tv/) | For downloading and managing TV episodes |
| [Transmission](https://transmissionbt.com/) | BitTorrent client, with OpenVPN when you have a supported VPN provider |
| [YouTubeDL-Material](https://github.com/Tzahi12345/YoutubeDL-Material) | Self-hosted YouTube downloader built on Material Design |

</details>

<details>
<summary><b>Gaming</b> (3)</summary>

| Application | Description |
| --- | --- |
| [Minecraft Bedrock Server](https://www.minecraft.net/) | Bedrock server edition of the popular building and exploring game |
| [Minecraft Java Server](https://www.minecraft.net/) | Java server edition of the popular building and exploring game |
| [Valheim Server](https://github.com/mbround18/valheim-docker) | Valheim dedicated gameserver manager |

</details>

<details>
<summary><b>Home Automation</b> (7)</summary>

| Application | Description |
| --- | --- |
| [ESPHome](https://esphome.io/) | ESP8266/ESP32 programming and management for home automation |
| [Home Assistant](https://www.home-assistant.io) | Open source home automation |
| [Homebridge](https://homebridge.io) | Emulate the iOS HomeKit API |
| [Mosquitto](https://mosquitto.org) | Open source MQTT broker |
| [n8n](https://n8n.io/) | Node based workflow and automation service, like IFTTT |
| [openHAB](https://www.openhab.org/) | Vendor and technology agnostic open source home automation |
| [Zigbee2MQTT](https://www.zigbee2mqtt.io/) | Use Zigbee devices without the vendor's bridge or gateway, exposed over MQTT |

</details>

<details>
<summary><b>Media Serving</b> (16)</summary>

| Application | Description |
| --- | --- |
| [Audiobookshelf](https://www.audiobookshelf.org/) | Self-hosted audiobook and podcast server |
| [Calibre](https://calibre-ebook.com) | Powerful and easy to use e-book manager |
| [Calibre-web](https://github.com/janeczku/calibre-web) | Clean interface for browsing, reading and downloading eBooks from an existing Calibre database |
| [Emby](https://emby.media/) | Media streaming and management |
| [Immich](https://immich.app/) | High performance self-hosted photo and video backup |
| [Jellyfin](https://jellyfin.github.io) | The Free Software Media System |
| [Komga](https://komga.org/) | Media server for your comics, mangas, BDs and magazines |
| [MiniDLNA](https://sourceforge.net/projects/minidlna/) | Simple media server, fully compliant with DLNA/UPnP-AV clients |
| [MyMediaForAlexa](https://www.mymediaalexa.com/) | Stream your music collection to your Alexa devices |
| [navidrome](https://www.navidrome.org/) | Modern music server and streamer compatible with Subsonic/Airsonic |
| [Plex](https://www.plex.tv/) | Plex Media Server |
| [Romm](https://github.com/zurdi15/romm) | Game library manager focused on retro gaming |
| [Tautulli](http://tautulli.com/) | Monitor your Plex Media Server |
| [Tdarr](https://tdarr.io/) | Distributed transcoding automation for your media library |
| [Threadfin](https://github.com/Threadfin/Threadfin) | M3U proxy for Plex DVR and Emby/Jellyfin Live TV, based on xTeVe |
| [Ubooquity](http://vaemendis.net/ubooquity/) | Book and comic server |

</details>

<details>
<summary><b>Monitoring and Observability</b> (11)</summary>

| Application | Description |
| --- | --- |
| [Alloy](https://grafana.com/docs/alloy/latest/) | Ships local logs to a Grafana Loki instance |
| [Changedetection](https://github.com/dgtlmoon/changedetection.io) | Website change detection and monitoring |
| [Glances](https://nicolargo.github.io/glances/) | See the state of your system via a web browser |
| [Grafana](https://grafana.com/) | Query, visualise and alert on your data |
| [iSpy Agent DVR](https://www.ispyconnect.com/) | Video surveillance software |
| [Loki](https://grafana.com/oss/loki/) | Horizontally scalable, highly available, multi-tenant log aggregation |
| [Netdata](https://my-netdata.io/) | Comprehensive system monitoring |
| [Prometheus](https://prometheus.io/) | Time series database and monitoring system |
| [Speedtest-Tracker](https://github.com/alexjustesen/speedtest-tracker) | Continuously track your internet speed |
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | Self-hosted uptime monitoring with status pages and notifications |
| [Wireshark](https://www.wireshark.org/) | Widely-used network protocol analyser |

</details>

<details>
<summary><b>News</b> (3)</summary>

| Application | Description |
| --- | --- |
| [Fresh RSS](https://freshrss.org/) | Self-hosted RSS feed aggregator |
| [Miniflux](https://miniflux.app/) | RSS news reader |
| [RSS-Bridge](https://rss-bridge.github.io/rss-bridge/) | The RSS feed for websites missing it |

</details>

<details>
<summary><b>Other</b> (18)</summary>

| Application | Description |
| --- | --- |
| [Bitwarden](https://github.com/dani-garcia/vaultwarden) | Password manager (technically Vaultwarden, a lightweight Rust implementation) |
| [Firefly III](https://firefly-iii.org/) | Free and open source personal finance manager |
| [Gotify](https://gotify.net/) | Self-hosted server for sending push notifications |
| [Guacamole](https://guacamole.apache.org/) | Web based remote desktop gateway supporting VNC, RDP and SSH |
| [Mealie](https://hay-kot.github.io/mealie/) | Self-hosted recipe manager and meal planner |
| [Mumble](https://www.mumble.info) | Open source, low latency, high quality voice chat |
| [Nextcloud](https://nextcloud.com/) | Self-hosted Dropbox alternative |
| [Octoprint](https://octoprint.org/) | Control and monitor your 3D printer |
| [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | Scan, index and archive all your physical documents |
| [Piwigo](https://piwigo.org/) | Photo gallery software |
| [Silverbullet](https://silverbullet.md) | Note-taking application optimised for people with a hacker mindset |
| [Spoolman](https://github.com/Donkie/Spoolman) | Keep track of your inventory of 3D-printer filament spools |
| [Stirling PDF](https://github.com/Stirling-Tools/Stirling-PDF) | Merge, split, convert, OCR and sign PDFs locally |
| [The Lounge](https://thelounge.chat) | Web based always-on IRC client |
| [Traefik](https://traefik.io/) | Web proxy and SSL certificate manager |
| [Virtual Desktop](https://github.com/RattyDAVE/docker-ubuntu-xrdp-mate-custom) | A virtual desktop running on your NAS |
| [Wallabag](https://wallabag.org/) | Save and classify articles, read them later |
| [ZNC](https://wiki.znc.in/ZNC) | IRC bouncer to stay connected to favourite IRC networks |

</details>

<details>
<summary><b>System Tools</b> (19)</summary>

| Application | Description |
| --- | --- |
| [Apcupsd](http://www.apcupsd.org/) | Daemon for controlling APC UPSes |
| [Authelia](https://www.authelia.com/) | Single sign-on and two-factor authentication portal (requires configuration) |
| [Cloud Commander](https://cloudcmd.io/) | Dual panel file manager with integrated web console and text editor |
| [Cloudflare DDNS](https://hub.docker.com/r/joshuaavalon/cloudflare-ddns/) | Automatically update Cloudflare with your IP address |
| [DDNS Updater](https://github.com/qdm12/ddns-updater) | Dynamic DNS updater for several providers |
| [Dockhand](https://dockhand.pro/) | Docker management UI with Compose stacks, terminals, logs and backups |
| [Dozzle](https://dozzle.dev/) | Real-time log viewer for your Docker containers, in the browser |
| [Duplicacy](https://duplicacy.com/) | Web UI for the Duplicacy cloud backup program, with lock-free deduplication backups to multiple providers |
| [Duplicati](https://www.duplicati.com/) | For backing up your stuff |
| [healthchecks.io](https://healthchecks.io/) | Ensure your NAS is online and get notified otherwise |
| [Krusader](https://krusader.org/) | Twin panel file management |
| [Nebula Sync](https://github.com/lovelaze/nebula-sync) | Keep the configuration of multiple Pi-hole instances in sync |
| [netboot.xyz](https://netboot.xyz/) | PXE boot server |
| [Portainer](https://portainer.io/) | For managing Docker and running custom images |
| [Route53 DDNS](https://crazymax.dev/ddns-route53/) | Automatically update AWS Route53 with your IP address |
| [Syncthing](https://syncthing.net/) | Sync directories with another device |
| [Tailscale](https://tailscale.com/) | WireGuard based mesh VPN to reach your NAS and home network from anywhere |
| [TimeMachine](https://github.com/awlx/samba-timemachine) | Samba-based mac backup server |
| [Watchtower](https://github.com/v2tec/watchtower) | Monitor your Docker containers and update them when a new version is available |

</details>

## Documentation and Help

Read the docs at [hitluca.github.io/ansible-nas](https://hitluca.github.io/ansible-nas/), including [Securing Applications with Authelia](https://hitluca.github.io/ansible-nas/docs/applications/system-tools/authelia), the [Logging stack](https://hitluca.github.io/ansible-nas/docs/applications/stacks/logging/) and [migrating from FreeNAS](https://hitluca.github.io/ansible-nas/docs/further-configuration/migrating-from-freenas/). PRs for more documentation are always welcome. If you think you've found a bug, raise an [issue](https://github.com/HitLuca/ansible-nas/issues).

## Scope

Ansible-NAS can run anything that's in a Docker image, which is why Portainer is included. A NAS configuration is a pretty personal thing based on what you download, what media you view, how many photos you take...so it's difficult to please everyone. If specific functionality you want isn't included and you think others could benefit, add it and raise a PR!

It doesn't set up your disk partitions, primarily because getting it wrong can be incredibly destructive. That aside, configuring partitions is usually a one-time (or very infrequent) event, so there's not much to be gained by automating it. Check out the [docs](https://hitluca.github.io/ansible-nas/docs/) for recommended setups.

## How This Project Is Built

Parts of this repository are written with the help of large language models. Every role is personally tested against the application it deploys on my own hardware, and its molecule scenario has to pass in CI before anything merges. The [full explanation](https://hitluca.github.io/ansible-nas/docs/how-this-project-is-built) covers what is and isn't delegated.

## Contributing

Contributions are always welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## Thanks

[David Stephens](https://github.com/davestephens) for creating Ansible-NAS, and all of the awesome contributors to the original project!
