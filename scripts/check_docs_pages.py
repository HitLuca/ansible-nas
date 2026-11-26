#!/usr/bin/env python3
"""Check that every application role has a corresponding documentation page."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import role_defaults

# Infrastructure and template roles don't need doc pages.
SKIP_EXACT = ("hello_world",)
SKIP_PREFIX = "ansible-nas-"

# Doc filename exceptions: roles that use a different doc filename.
# Key = role directory name, Value = expected doc filename (without .md)
DOC_NAME_OVERRIDES = {
    "drone-ci": "drone-ci",
    "woodpecker-ci": "woodpecker-ci",
    "speedtest-tracker": "speedtest-tracker",
    "transmission-with-openvpn": "transmission-with-openvpn",
    "cloudflare_ddns": "cloudflare_ddns",
    "ddns_updater": "ddns_updater",
    "netbootxyz": "netbootxyz",
    "route53_ddns": "route53_ddns",
    "rssbridge": "rssbridge",
    "youtubedlmaterial": "youtubedlmaterial",
    "healthchecks.io": "healthchecks.io",
    "cloudflared": "cloudflared",
    "ispyagentdvr": "ispyagentdvr",
    "speedtest_tracker": "speedtest-tracker",
    "calibreweb": "calibre-web",
}


def _is_application(role: str) -> bool:
    """Whether the role must have a doc page."""
    return role not in SKIP_EXACT and not role.startswith(SKIP_PREFIX)


def _expected_doc_name(role: str) -> str:
    """Return the expected doc filename (without .md) for a role."""
    return DOC_NAME_OVERRIDES.get(role, role)


def problems(root: Path) -> list[str]:
    """Return list of error messages for roles missing doc pages."""
    messages: list[str] = []
    docs_dir = root / "website" / "docs" / "applications"

    for path in sorted(p for p in (root / "roles").iterdir() if p.is_dir()):
        role = path.name
        if not _is_application(role):
            continue

        expected_doc = _expected_doc_name(role)
        found = False
        for cat_dir in docs_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            doc_file = cat_dir / f"{expected_doc}.md"
            if doc_file.is_file():
                found = True
                break

        if not found:
            messages.append(
                f"roles/{role}: missing documentation page "
                f"(expected website/docs/applications/<category>/{expected_doc}.md)"
            )

    return messages


def main(
    argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT
) -> int:
    """Entry point."""
    del argv
    messages = problems(root)
    for message in messages:
        print(message)
    if messages:
        return 1
    print("All application roles have documentation pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
