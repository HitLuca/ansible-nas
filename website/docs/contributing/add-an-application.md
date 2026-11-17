---
sidebar_position: 2
---
# Add An Application

Adding a new application to Ansible-NAS is easy! First, set up your [development environment](./development-environment.md).

Then start by looking at the `hello_world` role - this includes everything that's expected to be included with a new application. Ensure the application includes tests and documentation; tests should ensure that the application starts and stops correctly.

## Places to edit

A new application touches the following files:

| File | What to add |
| --- | --- |
| `roles/<name>/defaults/main.yml` | Settings, starting with `<name>_enabled: false`, plus an `<name>_image_name` / `<name>_image_version` pair. Pin `<name>_image_version` to a real release rather than `latest`. |
| `roles/<name>/tasks/main.yml` | A start block gated on `when: <name>_enabled is true`, and a stop block gated on `is false` that removes the container. Reference the image as `{{ <name>_image_name }}:{{ <name>_image_version }}`; a literal `image:` fails `scripts/check_role_structure.py`. |
| `roles/<name>/templates/`, `roles/<name>/files/` | Only if the application needs them. |
| `roles/<name>/molecule/default/` | `molecule.yml`, `side_effect.yml`, `verify.yml` and `verify_stopped.yml`, following `hello_world` or any neighbouring role. |
| `nas.yml` | A `- role: <name>` entry with a matching tag, in alphabetical order. |
| `README.md` | The application in the "Available Applications" list, in alphabetical order. |
| `website/docs/applications/<category>/<name>.md` | This documentation page. Pick the category folder that fits and start the file with a `title:` frontmatter key. |
| `CHANGELOG.md` | Add the application to the `## Unreleased` "Added applications" line. |
| `.ansible-lint-ignore` | Only if the application's public variables genuinely cannot carry the role prefix. |

Nothing else needs editing: the molecule test matrix (`scripts/github_test_matrix.py`), the pytest harness (`tests/test_molecule.py`) and the docs sidebar (`website/sidebars.js`) all discover roles and pages automatically, and `group_vars/all.yml` holds no per-application settings.

## Replacing or removing an application

Replacing one application with a different one (or removing it outright) touches everything above plus:

1. Delete the old `roles/<name>/` and its doc page.
2. `CHANGELOG.md` — add a `## Unreleased` "Breaking" bullet naming the removed role. `scripts/check_breaking_changes.py` fails `make lint` without it, and a removal makes the next release a major one.
3. `website/docs/differences-from-upstream.md` — add a "Removed roles" table row pointing at the migration guide.
4. Add a `# Migrating from <old>` section to the replacement's doc page, saying plainly which data does not carry over. Check `seerr.md` and `audiobookshelf.md` for the pattern.

## Running the checks

```bash
make test ROLE=<name>
make lint
make check-ports
make check-images
```

`make check-ports` lists host ports claimed by more than one role, so it will also show clashes that predate your change — check that your new role doesn't add one.

`make check-images` asks each role's registry for its tags and reports pinned `<name>_image_version` values that have fallen behind. `make update-images` rewrites them in place, staying on the same major version. A scheduled workflow runs the check every week.

Run `make` on its own to list all available targets.

Note that molecule expands `molecule.yml` with `string.Template`, so a literal `$` in that file (a bcrypt hash, for example) must be written as `$$`.
