#!/usr/bin/env python3
"""Report pinned Docker image versions that lag behind their registry.

Ansible-NAS pins each application's image in ``roles/<role>/defaults/main.yml``
as a ``<role>_image_name`` / ``<role>_image_version`` pair (a few use
``_image_tag`` or embed the tag in a single ``_image`` value). This walks every
role, asks the registry for its tags, and reports the newest tag of the same
shape and major version.

    tests/check-image-versions.py             # report, exit 0
    tests/check-image-versions.py --check     # report, exit 1 when behind
    tests/check-image-versions.py --patch     # rewrite the pinned versions
    tests/check-image-versions.py --format markdown > report.md

Only ``docker.io``, ``ghcr.io``, ``lscr.io`` (LinuxServer's ghcr mirror),
``docker.n8n.io`` (a Docker Hub proxy) and ``quay.io`` are queried. Floating
tags (``latest``) are reported but never changed. So are tags that name a
channel (``beta``, ``alpine``), a commit, or a composite build such as Immich's
``14-vectorchord0.3.0-pgvectors0.2.0``: they are compared against nothing.

Each repository is asked for one page of tags: the newest 100 for Docker Hub,
1000 elsewhere. A pin that has fallen off the page is reported as
``truncated`` instead of ``ok`` - it may or may not be current, so it is not
silently passed. On a newest-first page a pin that *is* on the page is proven
current, since every newer tag was scanned.

``DOCKERHUB_USERNAME`` and ``DOCKERHUB_TOKEN`` are used, when set, to log in
and lift the anonymous Docker Hub rate limit (the same variables
``scan_images.py`` reads).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = REPO_ROOT / "roles"
TIMEOUT = 20
USER_AGENT = "ansible-nas-image-check/1.0"
HUB_LOGIN = "https://hub.docker.com/v2/users/login/"
HUB_TAGS = "https://hub.docker.com/v2/repositories/{path}/tags?page_size=100&ordering=last_updated"

ASSIGNMENT = re.compile(r"^(?P<key>[a-z0-9_]+):[ \t]*(?P<raw>.*)$")
REPO_KEY = re.compile(r"^(?P<prefix>.+)_(?:image_name|docker_image_name|image|docker_image)$")
VERSION_SUFFIXES = ("_image_version", "_image_tag")
CHANNEL_PREFIX = re.compile(
    r"^(?P<prefix>version|develop|nightly|stable|release|edge|beta|alpha)-", re.I
)
TAG_CORE = re.compile(r"^(?P<v>[vV]?)(?P<core>\d+(?:[._-]\d+)*)(?P<rest>.*)$")
REVISION_LETTER = re.compile(r"^(?P<letter>[a-z])(?=[._-]|$)", re.I)
COMMIT_TAG = re.compile(r"^(?:version-)?(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}$", re.I)
CHANNEL_TAG = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
VARIANT_BUILD = re.compile(r"[._-]?(?P<build>\d+)$")
DOTTED_NUMBER = re.compile(r"\d\.\d")
PRERELEASE = re.compile(r"(alpha|beta|rc|dev|nightly|test|edge|unstable|snapshot|preview)", re.I)
HARDCODED_IMAGE = re.compile(r"^\s*image:\s*(?P<value>[^\s#]+)", re.M)


class RegistryError(Exception):
    """A registry could not be queried."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Tag:
    """A version tag split into the pieces used for comparison."""

    prefix: str
    parts: tuple[int, ...]
    revision: int
    variant: str
    build: int

    @property
    def key(self) -> tuple[tuple[int, ...], int, int]:
        """Sort key that also orders revisions and rebuilds of the same version."""
        return self.parts, self.revision, self.build

    @property
    def prerelease(self) -> bool:
        """Whether the tag carries a pre-release marker, in its channel or suffix."""
        return bool(PRERELEASE.search(self.prefix + self.variant))


@dataclass(frozen=True)
class Unversioned:
    """A tag that names a channel, a commit or a composite build, not a version."""

    status: str
    detail: str


@dataclass
class ImageRef:
    """One pinned image found in a role's defaults."""

    role: str
    path: Path
    repo_key: str
    version_key: str | None
    repo: str
    version: str
    line: int


@dataclass(frozen=True)
class TagPage:
    """The tags fetched for one repository, and whether the registry had more."""

    names: list[str]
    complete: bool


@dataclass
class Result:
    """The verdict for one ImageRef."""

    ref: ImageRef
    status: str
    latest: str = ""
    detail: str = ""


def _unquote(raw: str) -> str:
    """Strip a YAML value's quotes and any trailing comment."""
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        quote = raw[0]
        end = raw.find(quote, 1)
        return raw[1:end] if end != -1 else raw[1:]
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def _read_assignments(path: Path) -> dict[str, tuple[str, int]]:
    """Map each top-level ``key: value`` in *path* to (value, line number)."""
    assignments: dict[str, tuple[str, int]] = {}
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        match = ASSIGNMENT.match(line)
        if match:
            assignments[match["key"]] = (_unquote(match["raw"]), number)
    return assignments


def _split_repo_tag(value: str) -> tuple[str, str]:
    """Split ``repo:tag`` without breaking a ``host:port/repo`` reference."""
    repo, separator, tag = value.rpartition(":")
    if separator and "/" not in tag:
        return repo, tag
    return value, ""


def _refs_in_role(role_dir: Path) -> list[ImageRef]:
    """Find every image reference declared in one role's defaults."""
    path = role_dir / "defaults" / "main.yml"
    if not path.is_file():
        return []
    assignments = _read_assignments(path)
    refs: list[ImageRef] = []
    for key, (value, line) in assignments.items():
        match = REPO_KEY.match(key)
        if not match or not value or "{{" in value:
            continue
        prefix = match["prefix"]
        version_key = next(
            (prefix + suffix for suffix in VERSION_SUFFIXES if prefix + suffix in assignments),
            None,
        )
        if version_key is not None:
            version, version_line = assignments[version_key]
            repo = value
        else:
            repo, version = _split_repo_tag(value)
            version_line = line
        refs.append(
            ImageRef(
                role=role_dir.name,
                path=path,
                repo_key=key,
                version_key=version_key,
                repo=repo,
                version=version,
                line=version_line,
            )
        )
    return refs


def discover(only: Iterable[str] = ()) -> list[ImageRef]:
    """Collect the image references of every role (optionally filtered)."""
    wanted = set(only)
    refs: list[ImageRef] = []
    for role_dir in sorted(p for p in ROLES_DIR.iterdir() if p.is_dir()):
        if wanted and role_dir.name not in wanted:
            continue
        refs.extend(_refs_in_role(role_dir))
    return refs


def split_host(repo: str) -> tuple[str, str]:
    """Split ``host/path``; a bare ``namespace/name`` defaults to docker.io."""
    first, _, rest = repo.partition("/")
    if rest and ("." in first or ":" in first or first == "localhost"):
        return first, rest
    return "docker.io", repo


def _hub_credentials() -> tuple[str, str] | None:
    """The Docker Hub username and token, or None when either is unset."""
    username = os.environ.get("DOCKERHUB_USERNAME", "").strip()
    password = os.environ.get("DOCKERHUB_TOKEN", "").strip()
    if not username or not password:
        return None
    return username, password


@lru_cache(maxsize=None)
def _hub_login(username: str, password: str) -> str:
    """Exchange the credentials for the JWT that Docker Hub's web API accepts."""
    payload = _fetch(
        HUB_LOGIN,
        data=json.dumps({"username": username, "password": password}).encode(),
    )[0]
    return payload.get("token", "")


def _hub_authorization() -> str | None:
    """The ``Authorization`` header for Docker Hub, or None to query anonymously.

    Uses the same variables as ``scan_images.py``. A username without a token
    is ignored rather than sent as an empty password.
    """
    credentials = _hub_credentials()
    if credentials is None:
        return None
    token = _hub_login(*credentials)
    return f"JWT {token}" if token else None


def _fetch(
    url: str,
    token: str | None = None,
    authorization: str | None = None,
    data: bytes | None = None,
) -> tuple[dict, dict[str, str]]:
    """Request *url*, retrying transient failures, and decode the JSON body + headers."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data:
        headers["Content-Type"] = "application/json"
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(url, headers=headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                body = json.loads(response.read().decode())
                return body, {name.lower(): value for name, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise RegistryError(f"HTTP {exc.code}", exc.code) from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(2**attempt)
    raise RegistryError(str(last_error))


def _docker_hub_tags(path: str) -> TagPage:
    """Return the newest tags of a Docker Hub repository, newest update first.

    One page of 100 is enough: the tags of each release cluster at the top, and
    a pin that has fallen off the page is reported as ``truncated`` rather than
    guessed at. Paginating instead is not an option - linuxserver/radarr alone
    carries 19k tags - so the ordering is what makes a single page sufficient.
    """
    if "/" not in path:
        path = f"library/{path}"
    try:
        authorization = _hub_authorization()
    except RegistryError as exc:
        if exc.status != 401:
            raise
        raise RegistryError("Docker Hub rejected DOCKERHUB_USERNAME/DOCKERHUB_TOKEN", 401) from exc
    payload, _ = _fetch(HUB_TAGS.format(path=urllib.parse.quote(path, safe="/")),
                        authorization=authorization)
    return TagPage(
        [entry["name"] for entry in payload.get("results", [])],
        complete=not payload.get("next"),
    )


def _ghcr_tags(path: str) -> TagPage:
    """Return the tags of a GitHub Container Registry repository."""
    scope = urllib.parse.quote(f"repository:{path}:pull", safe="")
    token = _fetch(f"https://ghcr.io/token?service=ghcr.io&scope={scope}")[0].get("token", "")
    payload, headers = _fetch(f"https://ghcr.io/v2/{path}/tags/list?n=1000", token=token)
    return TagPage(payload.get("tags") or [], complete="next" not in headers.get("link", ""))


def _quay_tags(path: str) -> TagPage:
    """Return the active tags of a Quay repository."""
    url = f"https://quay.io/api/v1/repository/{path}/tag/?limit=100&onlyActiveTags=true"
    payload, _ = _fetch(url)
    return TagPage(
        [entry["name"] for entry in payload.get("tags", [])],
        complete=not payload.get("has_additional"),
    )


def fetch_tags(repo: str) -> TagPage:
    """Return every tag of *repo*, mapping known registry mirrors."""
    host, path = split_host(repo)
    if host in ("docker.io", "index.docker.io", "registry-1.docker.io"):
        return _docker_hub_tags(path)
    if host == "ghcr.io":
        return _ghcr_tags(path)
    if host in ("lscr.io", "docker.n8n.io"):
        # Both are proxies over Docker Hub; ghcr.io/linuxserver carries
        # arch-prefixed build tags (amd64-v1.2.3-ls4) instead.
        return _docker_hub_tags(path)
    if host == "quay.io":
        return _quay_tags(path)
    raise RegistryError(f"unsupported registry {host}")


def _variant_and_build(rest: str) -> tuple[str, int]:
    """Split a tag's suffix into its remaining shape and a trailing build number."""
    text = rest.strip("._-").lower()
    match = VARIANT_BUILD.search(text)
    if match is None:
        return text, 0
    return text[: match.start()], int(match["build"])


def _unversioned(tag: str) -> Unversioned:
    """Describe a tag whose text carries no leading version number."""
    if CHANNEL_TAG.match(tag):
        return Unversioned("channel", "channel tag")
    return Unversioned("unrecognized", "tag is not a version")


def _parse_tag(tag: str) -> Tag | Unversioned:
    """Split *tag* into its comparable pieces, or describe why it has no version."""
    text = tag.strip()
    if COMMIT_TAG.match(text):
        return Unversioned("commit", "pinned to a commit")
    prefix_match = CHANNEL_PREFIX.match(text)
    prefix = f"{prefix_match['prefix'].lower()}-" if prefix_match else ""
    core_match = TAG_CORE.match(text[len(prefix):])
    if core_match is None:
        return _unversioned(text)
    parts = tuple(int(part) for part in re.split(r"[._-]", core_match["core"]))
    rest = core_match["rest"]
    revision = 0
    if len(parts) == 3 and parts[0] >= 1900:
        # Only date cores take a revision letter (2026-07-14c); elsewhere the
        # letter begins the suffix (12.4ubu2604-ls59).
        letter = REVISION_LETTER.match(rest)
        if letter:
            revision = ord(letter["letter"].lower()) - ord("a") + 1
            rest = rest[letter.end():]
    shape, build = _variant_and_build(rest)
    if DOTTED_NUMBER.search(shape):
        # A version fragment in the suffix (vectorchord0.4.1) is a composite
        # build: the upstream release pins the exact combination, so there is
        # no safe automatic bump.
        return Unversioned("composite", "composite tag")
    return Tag(
        prefix=prefix,
        parts=parts,
        revision=revision,
        variant=re.sub(r"[._-]", "", shape),
        build=build,
    )


def _is_date(tag: Tag) -> bool:
    """Whether the tag looks like a ``YYYY-MM-DD`` build rather than semver."""
    return len(tag.parts) == 3 and tag.parts[0] >= 1900


def _acceptable(current: Tag, candidate: Tag, allow_major: bool) -> bool:
    """Whether *candidate* is a plausible upgrade of *current*."""
    if candidate.prefix != current.prefix or candidate.variant != current.variant:
        return False
    if len(candidate.parts) != len(current.parts):
        return False
    if candidate.prerelease and not current.prerelease:
        return False
    if not allow_major and not _is_date(current) and candidate.parts[0] != current.parts[0]:
        return False
    return candidate.key > current.key


def _best_match(current: Tag, tags: Iterable[str], allow_major: bool) -> str | None:
    """Return the highest upgrade of *current* present in *tags*."""
    best: Tag | None = None
    name = ""
    for tag in tags:
        candidate = _parse_tag(tag)
        if not isinstance(candidate, Tag) or not _acceptable(current, candidate, allow_major):
            continue
        if best is None or candidate.key > best.key:
            best = candidate
            name = tag
    return name if best is not None else None


def _evaluate(
    ref: ImageRef,
    tags_by_repo: dict[str, TagPage],
    errors: dict[str, str],
    allow_major: bool,
) -> Result:
    """Decide whether *ref* is behind its registry."""
    if not ref.version or ref.version.lower() == "latest":
        detail = "pinned to latest" if ref.version else "no tag pinned"
        return Result(ref, "floating", detail=detail)
    current = _parse_tag(ref.version)
    if isinstance(current, Unversioned):
        return Result(ref, current.status, detail=current.detail)
    if ref.repo in errors:
        return Result(ref, "error", detail=errors[ref.repo])
    page = tags_by_repo[ref.repo]
    latest = _best_match(current, page.names, allow_major)
    if latest is not None:
        return Result(ref, "update", latest=latest)
    # A newest-first page proves the pin current when the pin is on it: every
    # newer tag was scanned above. Otherwise the list may hide a newer tag.
    if page.complete or ref.version in page.names:
        return Result(ref, "ok")
    return Result(ref, "truncated", detail="pinned tag not in the fetched page")


def _fetch_all(repos: list[str], jobs: int) -> tuple[dict[str, TagPage], dict[str, str]]:
    """Fetch each repository's tags once, returning (tags, errors)."""
    tags: dict[str, TagPage] = {}
    errors: dict[str, str] = {}

    def _one(repo: str) -> tuple[str, TagPage | None, str | None]:
        try:
            return repo, fetch_tags(repo), None
        except (RegistryError, OSError) as exc:
            return repo, None, str(exc)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for repo, found, error in pool.map(_one, repos):
            if found is not None:
                tags[repo] = found
            elif error is not None:
                errors[repo] = error
    return tags, errors


def evaluate(refs: Sequence[ImageRef], allow_major: bool, jobs: int) -> list[Result]:
    """Evaluate every ref, querying each registry endpoint only once."""
    queryable = {
        ref.repo
        for ref in refs
        if ref.version
        and ref.version.lower() != "latest"
        and isinstance(_parse_tag(ref.version), Tag)
    }
    tags_by_repo, errors = _fetch_all(sorted(queryable), jobs)
    return [_evaluate(ref, tags_by_repo, errors, allow_major) for ref in refs]


def patch(results: Iterable[Result]) -> list[str]:
    """Rewrite the version of every update result, returning a change log."""
    changes: list[str] = []
    grouped: dict[Path, list[Result]] = {}
    for result in results:
        if result.status == "update":
            grouped.setdefault(result.ref.path, []).append(result)
    for path, items in grouped.items():
        lines = path.read_text().splitlines(keepends=True)
        for item in sorted(items, key=lambda result: -result.ref.line):
            old, new = item.ref.version, item.latest
            index = item.ref.line - 1
            if item.ref.version_key is None:
                lines[index] = lines[index].replace(f":{old}", f":{new}", 1)
            else:
                match = re.search(
                    rf"(?P<key>{re.escape(item.ref.version_key)}\s*:\s*)"
                    rf"(?P<q>[\"']?){re.escape(old)}(?P=q)",
                    lines[index],
                )
                if match:
                    quote = match["q"]
                    lines[index] = (
                        f"{lines[index][:match.start()]}{match['key']}"
                        f"{quote}{new}{quote}{lines[index][match.end():]}"
                    )
            changes.append(
                f"{path.relative_to(REPO_ROOT)}:{item.ref.line}  "
                f"{item.ref.version_key or item.ref.repo_key}  {old} -> {new}"
            )
        path.write_text("".join(lines))
    return changes


def _hardcoded_images() -> list[tuple[str, str, str]]:
    """Find image references written straight into a role's tasks."""
    found: list[tuple[str, str, str]] = []
    for role_dir in sorted(p for p in ROLES_DIR.iterdir() if p.is_dir()):
        for task_file in sorted((role_dir / "tasks").glob("*.yml")):
            text = task_file.read_text()
            for match in HARDCODED_IMAGE.finditer(text):
                value = match["value"].strip("'\"")
                if "{{" not in value:
                    found.append((role_dir.name, task_file.name, value))
    return found


def _print_table(results: list[Result]) -> None:
    """Print the results as an aligned table."""
    rows = [
        (result.ref.role, result.ref.version_key or result.ref.repo_key,
         result.ref.version or "-", result.latest or "-", result.status)
        for result in results
    ]
    headers = ("Role", "Variable", "Current", "Latest", "Status")
    widths = [max(len(row[i]) for row in (*rows, headers)) for i in range(len(headers))]
    line = "  ".join(header.ljust(width) for header, width in zip(headers, widths))
    print(line)
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def _print_markdown(results: list[Result]) -> None:
    """Print the results as a Markdown summary for a workflow step."""
    print("## Pinned image versions")
    print()
    print("| Role | Variable | Current | Latest | Status |")
    print("| --- | --- | --- | --- | --- |")
    for result in results:
        print(
            f"| {result.ref.role} | {result.ref.version_key or result.ref.repo_key} "
            f"| {result.ref.version or '-'} | {result.latest or '-'} | {result.status} |"
        )
    print()
    print(_summary(results))


def _summary(results: list[Result]) -> str:
    """One line counting the results by status."""
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    updates = counts.get("update", 0)
    pinned = sum(1 for result in results if result.status != "floating")
    detail = ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))
    return f"{updates} of {pinned} pinned images are behind upstream ({detail})."


def _report(results: list[Result], output: str, verbose: bool) -> None:
    """Write the results in the requested format."""
    if output == "json":
        payload = [
            {
                "role": result.ref.role,
                "variable": result.ref.version_key or result.ref.repo_key,
                "repo": result.ref.repo,
                "current": result.ref.version,
                "latest": result.latest,
                "status": result.status,
                "detail": result.detail,
            }
            for result in results
        ]
        print(json.dumps(payload, indent=2))
    elif output == "markdown":
        _print_markdown(results)
    else:
        _print_table(results)
        print()
        print(_summary(results))
        for result in results:
            if result.detail and result.status != "floating":
                print(f"  {result.ref.role}: {result.detail} ({result.ref.repo})")
    if verbose:
        hardcoded = _hardcoded_images()
        print()
        print(f"Image references written into tasks/ (not checked): {len(hardcoded)}")
        for role, filename, value in hardcoded:
            print(f"  {role}/{filename}: {value}")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="exit 1 when any pinned image is behind"
    )
    parser.add_argument("--patch", action="store_true", help="rewrite the pinned versions in place")
    parser.add_argument(
        "--allow-major", action="store_true", help="consider major-version upgrades too"
    )
    parser.add_argument(
        "--role", action="append", default=[], metavar="ROLE", help="limit to one role"
    )
    parser.add_argument("--format", choices=("table", "markdown", "json"), default="table")
    parser.add_argument(
        "--jobs", type=int, default=6, help="registry requests in flight (default 6)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="also list images hardcoded in tasks/"
    )
    args = parser.parse_args(argv)

    refs = discover(args.role)
    if not refs:
        print("No image references found.", file=sys.stderr)
        return 1

    results = evaluate(refs, args.allow_major, args.jobs)
    updates = [result for result in results if result.status == "update"]

    if args.patch:
        for change in patch(updates):
            print(f"patched {change}")
        if not updates:
            print("Nothing to update.")
        return 0

    _report(results, args.format, args.verbose)
    if args.check and updates:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
