#!/usr/bin/env python3
"""Enforce the role anatomy documented in CLAUDE.md.

Every role has defaults, tasks and (unless exempt) a molecule scenario,
defaults/main.yml declares the role's enabled flag, and tasks/main.yml carries
the gated start/stop blocks. Catches new roles copied from something other
than roles/hello_world/ before the drift reaches the playbook.

The exemption lists are checked too: an exemption for a role that no longer
exists, or that now follows the convention, fails, so the lists cannot rot into
hiding a later regression.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable, Sequence

import role_defaults
from role_defaults import Role

# Roles that legitimately deviate from the standard anatomy. Keep each list
# sorted so exemptions are easy to audit.
NO_MOLECULE = (
    "ansible-nas-docker",
    "ansible-nas-general",
    "ansible-nas-users",
    "ddns_updater",
    "duplicati",
    "homepage",
    "logging",
    "loki",
    "minecraft-bedrock-server",
    "mumble",
    "promtail",
)
NO_DEFAULTS = ("ansible-nas-users",)
NO_ENABLED_FLAG = ("ansible-nas-docker", "ansible-nas-general")
NO_START_STOP_BLOCK = (
    "ansible-nas-docker",
    "ansible-nas-general",
    "ansible-nas-users",
    "logging",
    "stats",
)
# Roles whose enabled flag is not <role_name>_enabled.
UNCONVENTIONAL_FLAG = ("healthchecks.io", "logging")

MOLECULE_FILES = ("molecule.yml", "side_effect.yml", "verify.yml", "verify_stopped.yml")
# A literal image in tasks, quoted or not; a Jinja value starts with "{".
LITERAL_IMAGE = re.compile(r"""^\s+image:\s*["']?(?P<image>[^"'{\s][^"'\s]*)""", re.M)
IMAGE_DEFAULT = re.compile(r"_(?:docker_image|image|image_name)$")


def _tasks_main(role: Role) -> str:
    path = role.path / "tasks" / "main.yml"
    return path.read_text() if path.is_file() else ""


def _missing_molecule(role: Role) -> list[str]:
    return [f for f in MOLECULE_FILES if not (role.path / "molecule" / "default" / f).is_file()]


def _blocks(role: Role, flag: str) -> tuple[bool, bool]:
    """Whether tasks/main.yml has the start and the stop block for *flag*."""
    text = _tasks_main(role)
    start = re.search(rf"when: *{re.escape(flag)} is true", text) is not None
    stop = re.search(rf"when: *{re.escape(flag)} is false", text) is not None
    return start, stop


def anatomy(role: Role) -> list[str]:
    """Problems with the role's files, flag and start/stop blocks."""
    out: list[str] = []
    if not (role.path / "tasks" / "main.yml").is_file():
        out.append("missing tasks/main.yml")
    if role.name not in NO_MOLECULE:
        out += [f"missing molecule/default/{f}" for f in _missing_molecule(role)]
    if (role.path / "meta").is_dir():
        out.append("has a meta/ directory; this repo's roles do not use one")
    if role.name in NO_DEFAULTS:
        return out
    if not role.defaults_path.is_file():
        return [*out, "missing defaults/main.yml"]

    flag = role.flag
    if flag is None:
        if role.name not in NO_ENABLED_FLAG:
            out.append("defaults/main.yml has no <role>_enabled flag")
        return out
    if flag != role.conventional_flag and role.name not in UNCONVENTIONAL_FLAG:
        out.append(f"enabled flag '{flag}' should be '{role.conventional_flag}'")
    if role.name in NO_START_STOP_BLOCK:
        return out
    start, stop = _blocks(role, flag)
    if not start:
        out.append(f"tasks/main.yml has no 'when: {flag} is true' start block")
    if not stop:
        out.append(f"tasks/main.yml has no 'when: {flag} is false' stop block")
    return out


def images(role: Role) -> list[str]:
    """A role that starts containers takes its image from defaults, pinned.

    A literal image: in tasks is invisible to renovate.json and to
    make check-images.
    """
    texts = [path.read_text() for path in role.task_files()]
    if not any("docker_container" in text for text in texts):
        return []
    out: list[str] = []
    literal = [m["image"] for text in texts for m in LITERAL_IMAGE.finditer(text)]
    if literal:
        out.append(
            f"tasks hardcode an image ({' '.join(literal)}); "
            "use {{ <role>_image_name }}:{{ <role>_image_version }}"
        )
    if not role.defaults_path.is_file():
        return out
    if not any(IMAGE_DEFAULT.search(key) for key in role.defaults):
        return [*out, "defaults/main.yml declares no image for its containers"]
    for key in role.defaults:
        if key.endswith("_image_name"):
            prefix = key.removesuffix("_image_name")
            if role_defaults.version_key(role.defaults, prefix) is None:
                out.append(f"{key} has no {prefix}_image_version pin next to it")
    return out


def _flag_or_empty(role: Role) -> str:
    return role.flag or ""


def _exemptions() -> dict[str, tuple[Sequence[str], Callable[[Role], bool]]]:
    """Exemption list name -> (its roles, test that a role still needs it).

    Built at call time, so a test can swap the module-level lists.
    """
    return {
        "NO_MOLECULE": (NO_MOLECULE, lambda r: bool(_missing_molecule(r))),
        "NO_DEFAULTS": (NO_DEFAULTS, lambda r: not r.defaults_path.is_file()),
        "NO_ENABLED_FLAG": (NO_ENABLED_FLAG, lambda r: r.flag is None),
        "NO_START_STOP_BLOCK": (
            NO_START_STOP_BLOCK,
            lambda r: r.flag is None or not all(_blocks(r, _flag_or_empty(r))),
        ),
        "UNCONVENTIONAL_FLAG": (UNCONVENTIONAL_FLAG, lambda r: r.flag != r.conventional_flag),
    }


def stale_exemptions(roles: Sequence[Role]) -> list[str]:
    """Exemptions for roles that are gone or no longer deviate."""
    by_name = {role.name: role for role in roles}
    out: list[str] = []
    for list_name, (names, still_needed) in _exemptions().items():
        for name in names:
            role = by_name.get(name)
            if role is None:
                out.append(f"{list_name}: '{name}' is not a role any more; drop the exemption")
            elif not still_needed(role):
                out.append(f"{list_name}: '{name}' now follows the convention; drop the exemption")
    return out


def main(argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT) -> int:
    """Entry point."""
    del argv
    roles = role_defaults.discover(root)
    messages = [
        f"roles/{role.name}: {problem}"
        for role in roles
        for problem in (*anatomy(role), *images(role))
    ]
    messages += [f"scripts/check_role_structure.py {m}" for m in stale_exemptions(roles)]
    for message in messages:
        print(message)
    if messages:
        return 1
    print("All roles follow the standard structure.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
