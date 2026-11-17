---
title: "Audiobookshelf"
---

Homepage: [https://www.audiobookshelf.org/](https://www.audiobookshelf.org/)

Docker Image: [https://github.com/advplyr/audiobookshelf/pkgs/container/audiobookshelf](https://github.com/advplyr/audiobookshelf/pkgs/container/audiobookshelf)

Audiobookshelf is a self-hosted audiobook and podcast server. It streams your library to the web, Android and iOS apps, tracks listening progress, and downloads new podcast episodes.

## Usage

Set `audiobookshelf_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The web interface is at [http://ansible_nas_host_or_ip:8041](http://ansible_nas_host_or_ip:8041). The first account you create becomes the administrator.

The role mounts `audiobooks_root` at `/audiobooks` and `podcasts_root` at `/podcasts`. When you add a library in the web interface, point it at one of those container paths.

## Migrating from Booksonic

The `booksonic` role was removed. Audiobookshelf takes over the audiobook and podcast libraries, but the two applications store their data differently, and Audiobookshelf has no Booksonic importer: users, listening progress, bookmarks and podcast subscriptions do not carry over.

1. Back up `docker_home` and your shares.
2. Remove `booksonic_enabled` from your inventory, where it is now ignored, and set `audiobookshelf_enabled: true`.
3. Remove the old container, which the playbook no longer manages: `docker rm -f booksonic`.
4. Run the playbook. Audiobookshelf starts with an empty config in `docker_home/audiobookshelf`.
5. Create the administrator account on port 8041, then add one library per media type pointing at `/audiobooks` or `/podcasts`. Audiobookshelf scans the existing folders and matches the files.
6. Re-create the users and re-subscribe the podcasts by hand. Listening progress starts from zero.
7. Once the new server works, delete `docker_home/booksonic`: it holds only Booksonic's database and playlists, the audio files are untouched.

The host port changes from 4041 to 8041, and the `booksonic_*` variables no longer exist.
