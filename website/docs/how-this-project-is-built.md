---
sidebar_position: 1.6
title: "How This Project Is Built"
description: "How large language models are used in this repository, and what is still done and verified by hand"
---

Parts of this repository are written with the help of large language models, and it is worth being upfront about what that does and does not mean.

Most of the work here is mechanical: porting a Docker Compose stack into a role's `defaults/main.yml` and `tasks/main.yml`, writing the matching molecule scenario, adding the entry to `nas.yml`, the README table and a docs page, then keeping a hundred image pins current. That is exactly the kind of repetitive, checkable work an LLM speeds up, and this project would be considerably smaller without it.

What is not delegated:

* **Every role is personally tested.** A role only lands after I have run it against the application it deploys, on my own hardware. The molecule scenarios also have to pass in CI before anything merges.
* **Many new roles start from something real.** A good number of the applications added to this fork began as a working Docker Compose stack I was already running on my NAS, then got ported into an Ansible role. The Immich role, for example, was written to take over the multi-container stack I had running under Portainer — PostgreSQL and cache on their own volumes, optional GPU acceleration, extra library mounts — rather than a single generic container.
* **The judgement calls are mine.** Which applications to support, how a role's variables are shaped, what gets pinned, and how an upgrade preserves an existing deployment's data are decisions that come from operating this box, not from a model.

The test suite is what makes this checkable rather than a claim about how the YAML was produced: if a role is broken, the molecule scenario or the weekly integration run says so, whoever wrote it.
