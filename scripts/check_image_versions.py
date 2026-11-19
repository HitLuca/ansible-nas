#!/usr/bin/env python3
"""Report pinned Docker image versions that lag behind their registry.

Ansible-NAS pins each application's image in ``roles/<role>/defaults/main.yml``
as a ``<role>_image_name`` / ``<role>_image_version`` pair (a few use
``_image_tag`` or embed the tag in a single ``_image`` value). This walks every
role, asks the registry for its tags, and reports the newest tag of the same
shape and major version. A newer tag of a different major version is shown in
the Latest column too, as ``x.y.z (major)`` or ``a.b.c (+x.y.z major)`` next to
an update: visible, but not counted as behind and never patched unless
``--allow-major`` is given.

    scripts/check_image_versions.py             # report, exit 0
    scripts/check_image_versions.py --check     # report, exit 1 when behind
    scripts/check_image_versions.py --patch     # rewrite the pinned versions
    scripts/check_image_versions.py --format markdown > report.md

The table shows the publish date of the current and latest tags where the
registry reports one, so a source whose tags stopped updating (a moved or
abandoned repository) stands out as two far-past dates.

Only ``docker.io``, ``ghcr.io``, ``lscr.io`` (LinuxServer's ghcr mirror),
``docker.n8n.io`` (a Docker Hub proxy) and ``quay.io`` are queried. Floating
tags (``latest``) are reported but never changed. So are tags that name a
channel (``beta``, ``alpine``), a commit, or a composite build such as Immich's
``14-vectorchord0.3.0-pgvectors0.2.0``: they are compared against nothing.

Each repository's tag list is walked until it is complete, or - on Docker Hub
- until every pinned tag has been found or superseded by a newer one, so a pin
is proven current instead of reported ``truncated``. Docker Hub pages 100 tags
newest-update-first, ghcr.io pages 1000 lexically. ``truncated`` stays as the
fallback for any list that cannot be walked to a decision.

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

import role_defaults

REPO_ROOT = role_defaults.REPO_ROOT
ROLES_DIR = REPO_ROOT / "roles"
TIMEOUT = 20
USER_AGENT = "ansible-nas-image-check/1.0"
HUB_LOGIN = "https://hub.docker.com/v2/users/login/"
HUB_TAGS = "https://hub.docker.com/v2/repositories/{path}/tags?page_size=100&ordering=last_updated"

CHANNEL_PREFIX = re.compile(
    r"^(?P<prefix>version|develop|nightly|stable|release|edge|beta|alpha)-", re.I
)
TAG_CORE = re.compile(r"^(?P<v>[vV]?)(?P<core>\d+(?:[._-]\d+)*)(?P<rest>.*)$")
REVISION_LETTER = re.compile(r"^(?P<letter>[a-z])(?=[._-]|$)", re.I)
COMMIT_TAG = re.compile(r"^(?:version-)?(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}$", re.I)
CHANNEL_TAG = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
VARIANT_BUILD = re.compile(r"[._-]?(?P<build>\d+)$")
DOTTED_NUMBER = re.compile(r"\d\.\d")
PRERELEASE = re.compile(
    r"(alpha|beta|rc|dev|nightly|test|edge|unstable|snapshot|preview)", re.I
)
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
    # Whether the registry returned the most recently pushed tags first. Only
    # then does finding the pin on a truncated page prove nothing newer exists.
    newest_first: bool = True
    # tag -> YYYY-MM-DD publish date, where the registry reports one (ghcr
    # lists only names, so its entries stay empty).
    dates: dict[str, str] = field(default_factory=dict)


@dataclass
class Result:
    """The verdict for one ImageRef."""

    ref: ImageRef
    status: str
    latest: str = ""
    major_latest: str = ""
    detail: str = ""
    current_date: str = ""
    latest_date: str = ""

    @property
    def newest(self) -> str:
        """The Latest cell: the bump this script would apply, else the next major."""
        if self.latest and self.major_latest:
            return f"{self.latest} (+{self.major_latest} major)"
        return self.latest or (
            f"{self.major_latest} (major)" if self.major_latest else ""
        )


def _refs_in_role(role: role_defaults.Role) -> list[ImageRef]:
    """Find every image reference declared in one role's defaults."""
    refs: list[ImageRef] = []
    for key, entry in role.defaults.items():
        match = role_defaults.IMAGE_KEY.match(key)
        if not match or not entry.text or "{{" in entry.text:
            continue
        version_key = role_defaults.version_key(role.defaults, match["prefix"])
        if version_key is not None:
            repo, version = entry.text, role.text(version_key)
            line = role.defaults[version_key].line
        else:
            repo, version = role_defaults.split_repo_tag(entry.text)
            line = entry.line
        refs.append(
            ImageRef(
                role=role.name,
                path=role.defaults_path,
                repo_key=key,
                version_key=version_key,
                repo=repo,
                version=version,
                line=line,
            )
        )
    return refs


def discover(only: Iterable[str] = ()) -> list[ImageRef]:
    """Collect the image references of every role (optionally filtered)."""
    return [
        ref
        for role in role_defaults.discover(REPO_ROOT, only)
        for ref in _refs_in_role(role)
    ]


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
                raw = response.read()
                headers_out = {
                    name.lower(): value for name, value in response.headers.items()
                }
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise RegistryError(f"HTTP {exc.code}", exc.code) from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        else:
            try:
                body = json.loads(raw.decode())
            except (UnicodeDecodeError, ValueError) as exc:
                # A proxy or captive page answering 200 with HTML: fail this
                # repository instead of the whole run.
                raise RegistryError(f"non-JSON response from {url}") from exc
            if not isinstance(body, dict):
                raise RegistryError(f"unexpected JSON from {url}")
            return body, headers_out
        if attempt < 2:
            time.sleep(2**attempt)
    raise RegistryError(str(last_error))


def _published(entry: dict) -> str:
    """The ``YYYY-MM-DD`` a registry tag was published, or '' when unknown."""
    for key in ("last_updated", "last_pushed", "last_modified"):
        value = entry.get(key)
        if not value:
            continue
        if isinstance(value, (int, float)):
            return time.strftime("%Y-%m-%d", time.gmtime(value))
        text = str(value)
        if len(text) >= 10 and text[:4].isdigit() and text[4] == "-":
            return text[:10]
    return ""


def _backfill_pin_dates(
    path: str, pins: Iterable[str], dates: dict[str, str], authorization: str | None
) -> None:
    """Fill dates for pins superseded before their own tag was paged.

    Docker Hub lists newest-first, so a behind pin is dropped from the paging
    queue as soon as a newer tag appears - often before its own entry. Fetch
    each such pin individually to keep the Current date populated.
    """
    base = f"https://hub.docker.com/v2/repositories/{urllib.parse.quote(path, safe='/')}/tags/"
    for pin in pins:
        if pin in dates:
            continue
        try:
            detail, _ = _fetch(
                base + urllib.parse.quote(pin, safe=""), authorization=authorization
            )
            published = _published(detail)
            if published:
                dates[pin] = published
        except RegistryError:
            pass


def _docker_hub_tags(
    path: str, pins: Iterable[str] = (), allow_major: bool = False
) -> TagPage:
    """Return Docker Hub tags newest-update-first, paging past a fallen-off pin.

    Ordering is by last update, not version, so 100 re-pushed tags can bury a
    current pin off page one. Page until every *pins* is resolved (its tag
    found, or a newer acceptable tag seen) or the list ends. A repo with 19k
    tags (linuxserver/radarr) costs extra requests only when a pin has fallen
    off page one, and a behind pin stops as soon as its successor appears.
    """
    if "/" not in path:
        path = f"library/{path}"
    try:
        authorization = _hub_authorization()
    except RegistryError as exc:
        if exc.status != 401:
            raise
        raise RegistryError(
            "Docker Hub rejected DOCKERHUB_USERNAME/DOCKERHUB_TOKEN", 401
        ) from exc
    remaining: dict[str, Tag] = {}
    for pin in pins:
        parsed = _parse_tag(pin)
        if isinstance(parsed, Tag):
            remaining[pin] = parsed
    names: list[str] = []
    dates: dict[str, str] = {}
    url: str | None = HUB_TAGS.format(path=urllib.parse.quote(path, safe="/"))
    while url:
        payload, _ = _fetch(url, authorization=authorization)
        for entry in payload.get("results", []):
            name = entry["name"]
            names.append(name)
            published = _published(entry)
            if published:
                dates[name] = published
        url = payload.get("next")
        remaining = {
            pin: current
            for pin, current in remaining.items()
            if pin not in names and _best_match(current, names, allow_major) is None
        }
        if not remaining:
            break
    _backfill_pin_dates(path, pins, dates, authorization)
    return TagPage(names, complete=not url, dates=dates)


def _next_link(link: str) -> str | None:
    """The URL of the ``rel="next"`` entry in a Link header, or None."""
    for part in link.split(","):
        if 'rel="next"' in part:
            start, end = part.find("<"), part.find(">")
            if start != -1 and end != -1:
                return part[start + 1 : end]
    return None


def _ghcr_tags(path: str) -> TagPage:
    """Return every tag of a GitHub Container Registry repository."""
    scope = urllib.parse.quote(f"repository:{path}:pull", safe="")
    token = _fetch(f"https://ghcr.io/token?service=ghcr.io&scope={scope}")[0].get(
        "token", ""
    )
    names: list[str] = []
    url: str | None = f"https://ghcr.io/v2/{path}/tags/list?n=1000"
    while url:
        payload, headers = _fetch(url, token=token)
        names.extend(payload.get("tags") or [])
        url = _next_link(headers.get("link", ""))
        # ghcr returns the next link as a bare path, not an absolute URL.
        if url:
            url = urllib.parse.urljoin("https://ghcr.io", url)
    # Lexical order here, but a complete list makes the order irrelevant.
    return TagPage(names, complete=True, newest_first=False)


def _quay_tags(path: str) -> TagPage:
    """Return the active tags of a Quay repository."""
    url = f"https://quay.io/api/v1/repository/{path}/tag/?limit=100&onlyActiveTags=true"
    payload, _ = _fetch(url)
    names: list[str] = []
    dates: dict[str, str] = {}
    for entry in payload.get("tags", []):
        name = entry["name"]
        names.append(name)
        published = _published(entry)
        if published:
            dates[name] = published
    return TagPage(names, complete=not payload.get("has_additional"), dates=dates)


def fetch_tags(
    repo: str, pins: Iterable[str] = (), allow_major: bool = False
) -> TagPage:
    """Return every tag of *repo*, mapping known registry mirrors."""
    host, path = split_host(repo)
    if host in ("docker.io", "index.docker.io", "registry-1.docker.io"):
        return _docker_hub_tags(path, pins, allow_major)
    if host == "ghcr.io":
        return _ghcr_tags(path)
    if host in ("lscr.io", "docker.n8n.io"):
        # Both are proxies over Docker Hub; ghcr.io/linuxserver carries
        # arch-prefixed build tags (amd64-v1.2.3-ls4) instead.
        return _docker_hub_tags(path, pins, allow_major)
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
    core_match = TAG_CORE.match(text[len(prefix) :])
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
            rest = rest[letter.end() :]
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
    if (
        not allow_major
        and not _is_date(current)
        and candidate.parts[0] != current.parts[0]
    ):
        return False
    return candidate.key > current.key


def _best_match(current: Tag, tags: Iterable[str], allow_major: bool) -> str | None:
    """Return the highest upgrade of *current* present in *tags*."""
    best: Tag | None = None
    name = ""
    for tag in tags:
        candidate = _parse_tag(tag)
        if not isinstance(candidate, Tag) or not _acceptable(
            current, candidate, allow_major
        ):
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
    # Shown next to the update, or alone when that is the only newer tag.
    # Only a tag whose first component moves is a major bump; date pins have
    # no major, their year is part of the release number.
    major = ""
    if not allow_major and not _is_date(current):
        best = _best_match(current, page.names, True)
        parsed = _parse_tag(best) if best is not None else None
        if isinstance(parsed, Tag) and parsed.parts[0] != current.parts[0]:
            major = best or ""
    current_date = page.dates.get(ref.version, "")
    latest_date = page.dates.get(latest or major, "")
    if latest is not None:
        return Result(
            ref, "update", latest=latest, major_latest=major,
            current_date=current_date, latest_date=latest_date,
        )
    # A newest-first page proves the pin current when the pin is on it: every
    # newer tag was scanned above. Otherwise the list may hide a newer tag.
    if page.complete or (page.newest_first and ref.version in page.names):
        return Result(
            ref, "ok", major_latest=major,
            current_date=current_date, latest_date=latest_date,
        )
    return Result(ref, "truncated", detail="pinned tag not in the fetched page")


def _progress(done: int, total: int) -> None:
    """Show fetch progress on stderr, only when it is a terminal (not in CI/pipes)."""
    if not sys.stderr.isatty():
        return
    filled = "#" * (done * 20 // total)
    print(
        f"\rFetching tags [{filled:<20}] {done}/{total}",
        end="\n" if done >= total else "",
        file=sys.stderr,
    )


def _fetch_all(
    repos: list[str],
    jobs: int,
    pins_by_repo: dict[str, list[str]] | None = None,
    allow_major: bool = False,
) -> tuple[dict[str, TagPage], dict[str, str]]:
    """Fetch each repository's tags once, returning (tags, errors)."""
    pins_by_repo = pins_by_repo or {}
    tags: dict[str, TagPage] = {}
    errors: dict[str, str] = {}

    def _one(repo: str) -> tuple[str, TagPage | None, str | None]:
        try:
            return repo, fetch_tags(repo, pins_by_repo.get(repo, ()), allow_major), None
        except (RegistryError, OSError) as exc:
            return repo, None, str(exc)

    total = len(repos)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(_one, repo) for repo in repos]
        for done, future in enumerate(as_completed(futures), 1):
            repo, found, error = future.result()
            _progress(done, total)
            if found is not None:
                tags[repo] = found
            elif error is not None:
                errors[repo] = error
    return tags, errors


def evaluate(refs: Sequence[ImageRef], allow_major: bool, jobs: int) -> list[Result]:
    """Evaluate every ref, querying each registry endpoint only once."""
    pins_by_repo: dict[str, list[str]] = {}
    for ref in refs:
        if (
            ref.version
            and ref.version.lower() != "latest"
            and isinstance(_parse_tag(ref.version), Tag)
        ):
            pins_by_repo.setdefault(ref.repo, []).append(ref.version)
    tags_by_repo, errors = _fetch_all(sorted(pins_by_repo), jobs, pins_by_repo, allow_major)
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
            before = lines[index]
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
            if lines[index] == before:
                print(
                    f"could not patch {path.relative_to(REPO_ROOT)}:{item.ref.line} "
                    f"({old} -> {new}); edit it by hand",
                    file=sys.stderr,
                )
                continue
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
        (
            result.ref.role,
            result.ref.version_key or result.ref.repo_key,
            result.ref.version or "-",
            result.current_date,
            result.newest or "-",
            result.latest_date,
            result.status,
        )
        for result in results
    ]
    headers = ("Role", "Variable", "Current", "Date", "Latest", "Date", "Status")
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
    print("| Role | Variable | Current | Date | Latest | Date | Status |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for result in results:
        print(
            f"| {result.ref.role} | {result.ref.version_key or result.ref.repo_key} "
            f"| {result.ref.version or '-'} | {result.current_date} "
            f"| {result.newest or '-'} | {result.latest_date} | {result.status} |"
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
                "current_date": result.current_date,
                "latest": result.latest,
                "latest_date": result.latest_date,
                "major_latest": result.major_latest,
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
    parser.add_argument(
        "--patch", action="store_true", help="rewrite the pinned versions in place"
    )
    parser.add_argument(
        "--allow-major", action="store_true", help="consider major-version upgrades too"
    )
    parser.add_argument(
        "--role", action="append", default=[], metavar="ROLE", help="limit to one role"
    )
    parser.add_argument(
        "--format", choices=("table", "markdown", "json"), default="table"
    )
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
