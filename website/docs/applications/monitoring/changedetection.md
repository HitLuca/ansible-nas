---
title: "Changedetection"
---

Homepage: [https://github.com/dgtlmoon/changedetection.io](https://github.com/dgtlmoon/changedetection.io)

Changedetection.io is a free, open-source website change detection and monitoring tool. It watches web pages for changes — price drops, restocks, forum posts, documentation updates — and notifies you by email, Discord, Slack, Telegram and more, or exposes the changes as an RSS feed.

It stores a snapshot of each watched page and compares it on a schedule, so it can detect changes on sites that have no feed of their own.

## Usage

Set `changedetection_enabled: true` in your `inventories/<your_inventory>/group_vars/nas.yml` file.

The Changedetection web interface can be found at [http://ansible_nas_host_or_ip:5000](http://ansible_nas_host_or_ip:5000).
