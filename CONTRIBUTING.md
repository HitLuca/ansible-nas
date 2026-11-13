# Contributing

Contributing to Ansible-NAS is easy! Add your functionality, then raise a pull request on GitHub. A few things to bear in mind:

## Development Environment

* Development of Ansible-NAS is carried out in [JetBrains PyCharm](https://www.jetbrains.com/?from=Ansible-NAS) on Linux - you'll get some nice recommended extensions and task setups if you do the same.
* You'll need a working Python 3 environment, Docker (to run tests) and [pre-commit](https://pre-commit.com) installed - `pip install -r requirements-dev.txt`.

## General Stuff

* **Restrict pull requests to one piece of functionality or bugfix at a time.**
* Ensure that your changes aren't going to break the GitHub builds. You can run the Pre-commit checks manually (it's not yet configured to run on every commit) using the VSCode task.
* Ensure that your PR only changes files required for your functionality or bugfix. Random changes in other files will result in your PR being rejected.
* Don't mess with line endings, or change spaces for tabs. They're fine how they are.
* Please know that your efforts are appreciated, thanks! :+1:

## Adding a new application

So you want to add a new application. Great!

Start by looking at the `hello_world` example. Following this structure is the most likely way of getting your PR approved. Leaving out things the `hello_world` example includes (ie docs, tests) will definitely result in your PR being rejected.

A new application touches these places:

* `roles/<name>/` - the role itself:
  * `defaults/main.yml`, starting with `<name>_enabled: false` (the `tests/check-enabled-vars.sh` check fails without it), an `<name>_image_name` / `<name>_image_version` pair, and pinning `<name>_image_version` to a real release rather than `latest`.
  * `tasks/main.yml`, with a start block gated on `when: <name>_enabled is true` and a stop block gated on `is false` that removes the container. Reference the image as `{{ <name>_image_name }}:{{ <name>_image_version }}` rather than writing it out — `tests/check-role-structure.sh` rejects a literal `image:`.
  * `templates/` and `files/`, if the application needs them.
  * `molecule/default/` - `molecule.yml`, `side_effect.yml`, `verify.yml` and `verify_stopped.yml`. Copy the layout from `hello_world` or any neighbouring role.
* `nas.yml` - add `- role: <name>` with a matching tag, in alphabetical order.
* `README.md` - add the application to the "Available Applications" list, in alphabetical order.
* `website/docs/applications/<category>/<name>.md` - the documentation page, filed under the category folder that fits (see the existing folders). Start it with a `title:` frontmatter key.
* `.ansible-lint-ignore` - only if the application's public variables genuinely cannot carry the role prefix.

Nothing else needs editing. The molecule test matrix (`tests/github-test-matrix.sh`), the pytest harness (`tests/test_molecule.py`) and the docs sidebar (`website/sidebars.js`) all discover roles and pages automatically, and `group_vars/all.yml` holds no per-application settings.

Before opening the PR, run the role's tests and the lint checks:

```bash
make test ROLE=<name>
make lint
make check-ports
make check-images
```

`make check-images` reports `<name>_image_version` pins that have fallen behind their registry; `make update-images` rewrites them in place (same major version only). A scheduled workflow runs the check weekly.

`make scan-images` looks inside the pinned images instead of at their tags: Trivy reports CRITICAL and HIGH CVEs that a version bump would clear. It needs `trivy` on your `PATH`, and the weekly Image scan workflow files whatever it finds on a tracking issue rather than failing the build. The issue leads with a per-role summary table and folds each image's CVE list into a collapsible block, so the full list lives in the run's `image-scan` artifact instead.

Run `make` on its own to list all available targets.

Note that molecule expands `molecule.yml` with `string.Template`, so a literal `$` in that file (a bcrypt hash, for example) must be written as `$$`.
