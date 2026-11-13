#!/usr/bin/env python3
"""Report pinned container images that contain known vulnerabilities.

``check_image_versions.py`` answers "is this pin behind?". This answers "is this
pin vulnerable?". Renovate and Dependabot only compare a tag against a registry;
they never look inside the image, so a CVE in its OS packages or bundled
libraries stays invisible to them. Trivy unpacks each pinned image and queries
its vulnerability database.

    tests/scan_images.py                       # report, exit 0
    tests/scan_images.py --check               # report, exit 1 on findings
    tests/scan_images.py --format markdown     # issue body or job summary
    tests/scan_images.py --role nextcloud      # one role only
    tests/scan_images.py --include-unfixed     # also findings with no fix

Findings with no fix are hidden by default: a bump cannot clear them, so they
are noise for a repo that only pins tags. Trivy must be on ``PATH``; pass
``--trivy`` to point at a different binary.

Docker Hub credentials in ``DOCKERHUB_USERNAME``/``DOCKERHUB_TOKEN`` are used
for docker.io images only, which lifts the anonymous pull limit. Set them in CI
as repo secrets; locally, Trivy already reads ``docker login``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import check_image_versions as inventory

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
RANK = {severity: index for index, severity in enumerate(SEVERITIES)}
SCAN_TIMEOUT = 600
DB_TIMEOUT = 300


@dataclass
class Finding:
    """One vulnerability reported by Trivy."""

    vuln_id: str
    package: str
    installed: str
    fixed: str
    severity: str
    title: str


@dataclass
class Scan:
    """The verdict for one pinned image."""

    ref: inventory.ImageRef
    findings: list[Finding] = field(default_factory=list)
    error: str = ""

    @property
    def image(self) -> str:
        """The ``repo:tag`` reference that was handed to Trivy."""
        return f"{self.ref.repo}:{self.ref.version}" if self.ref.version else self.ref.repo

    def count(self, severity: str) -> int:
        """Number of findings at exactly *severity*."""
        return sum(1 for finding in self.findings if finding.severity == severity)


@dataclass(frozen=True)
class Options:
    """How to invoke Trivy."""

    binary: str = "trivy"
    severities: tuple[str, ...] = ("CRITICAL", "HIGH")
    ignore_unfixed: bool = True
    jobs: int = 4
    timeout: int = SCAN_TIMEOUT
    # Docker Hub credentials, for the anonymous pull limit CI shares with
    # everything else on its runner. Empty credentials mean anonymous pulls.
    username: str = ""
    password: str = field(default="", repr=False)


def _run(
    binary: str,
    args: Sequence[str],
    timeout: int,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one Trivy command without raising on a non-zero exit."""
    return subprocess.run(
        [binary, *args], capture_output=True, text=True, timeout=timeout, check=False, env=env
    )


def _credentials(options: Options, ref: inventory.ImageRef) -> dict[str, str] | None:
    """Environment carrying the Docker Hub credentials, or None to pull anonymously.

    Trivy applies ``TRIVY_USERNAME``/``TRIVY_PASSWORD`` to whatever registry it
    is given, so they are set only for docker.io: sending a Docker Hub token to
    ghcr.io breaks the anonymous pull that registry already allows.
    """
    if not options.username or inventory.split_host(ref.repo)[0] != "docker.io":
        return None
    return {**os.environ, "TRIVY_USERNAME": options.username, "TRIVY_PASSWORD": options.password}


def prepare_database(options: Options) -> str:
    """Download the database once; return an error message, or an empty string."""
    try:
        result = _run(options.binary, ["image", "--download-db-only", "--quiet"], DB_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"Could not run {options.binary}: {error}"
    if result.returncode != 0:
        return f"Could not download the Trivy database:\n{result.stderr.strip()}"
    return ""


def _parse(payload: dict) -> list[Finding]:
    """Turn one Trivy JSON report into findings."""
    findings: list[Finding] = []
    for result in payload.get("Results") or []:
        for item in result.get("Vulnerabilities") or []:
            findings.append(
                Finding(
                    vuln_id=str(item.get("VulnerabilityID") or ""),
                    package=str(item.get("PkgName") or ""),
                    installed=str(item.get("InstalledVersion") or ""),
                    fixed=str(item.get("FixedVersion") or ""),
                    severity=str(item.get("Severity") or "UNKNOWN").upper(),
                    title=str(item.get("Title") or ""),
                )
            )
    return findings


def scan(ref: inventory.ImageRef, options: Options) -> Scan:
    """Scan one pinned image."""
    scan_result = Scan(ref=ref)
    args = [
        "image",
        "--quiet",
        "--format",
        "json",
        "--scanners",
        "vuln",
        "--severity",
        ",".join(options.severities),
        "--skip-db-update",
        "--timeout",
        f"{options.timeout}s",
    ]
    if options.ignore_unfixed:
        args.append("--ignore-unfixed")
    args.append(scan_result.image)
    try:
        result = _run(
            options.binary, args, options.timeout + 60, _credentials(options, ref)
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        scan_result.error = f"{type(error).__name__}: {error}"
        return scan_result
    if result.returncode != 0:
        stderr = [line for line in result.stderr.strip().splitlines() if line.strip()]
        scan_result.error = stderr[-1] if stderr else f"trivy exited {result.returncode}"
        return scan_result
    try:
        scan_result.findings = _parse(json.loads(result.stdout or "{}"))
    except json.JSONDecodeError:
        scan_result.error = "unparseable Trivy output"
        return scan_result
    scan_result.findings.sort(
        key=lambda finding: (RANK.get(finding.severity, len(RANK)), finding.vuln_id)
    )
    return scan_result


def scan_all(refs: Sequence[inventory.ImageRef], options: Options) -> list[Scan]:
    """Scan every reference, *jobs* images at a time."""
    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        futures = [pool.submit(scan, ref, options) for ref in refs]
        return [future.result() for future in futures]


def _totals(scans: Sequence[Scan], severities: Sequence[str]) -> dict[str, int]:
    """Count findings per severity across every scan."""
    return {severity: sum(item.count(severity) for item in scans) for severity in severities}


def _summary(scans: Sequence[Scan], options: Options) -> str:
    """One line counting affected images and errors."""
    affected = [item for item in scans if item.findings]
    errors = [item for item in scans if item.error]
    totals = _totals(scans, options.severities)
    if not affected:
        line = f"No findings in {len(scans)} pinned images"
    else:
        detail = ", ".join(f"{count} {severity.lower()}" for severity, count in totals.items())
        verb = "has" if len(affected) == 1 else "have"
        line = f"{len(affected)} of {len(scans)} pinned images {verb} findings ({detail})"
    if errors:
        line += f"; {len(errors)} could not be scanned"
    return f"{line}."


def _sorted_affected(scans: Sequence[Scan], options: Options) -> list[Scan]:
    """Affected scans, worst first, then by role."""
    def key(item: Scan) -> tuple:
        totals = tuple(-item.count(severity) for severity in options.severities)
        return (*totals, item.ref.role)

    return sorted((item for item in scans if item.findings), key=key)


def _cell(text: str) -> str:
    """Escape a value for a Markdown table cell."""
    return text.replace("|", "\\|")


def _markdown(scans: Sequence[Scan], options: Options, max_details: int) -> list[str]:
    """Render the report as Markdown lines."""
    mode = "fixable findings only" if options.ignore_unfixed else "including unfixed findings"
    lines = [
        "## Container image vulnerabilities",
        "",
        f"Trivy scanned {len(scans)} pinned images at "
        f"{', '.join(options.severities)} severity ({mode}).",
        "",
        f"**{_summary(scans, options)}**",
    ]
    affected = _sorted_affected(scans, options)
    if affected:
        headers = ("Role", "Image", *(severity.title() for severity in options.severities))
        lines += ["", "| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for item in affected:
            cells = (
                item.ref.role,
                item.image,
                *(str(item.count(severity)) for severity in options.severities),
            )
            lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " |")

    total_findings = sum(len(item.findings) for item in affected)
    shown = 0
    details: list[str] = []
    for item in affected:
        if shown >= max_details:
            break
        details += ["", f"### {item.ref.role} — `{item.image}`", ""]
        details.append("| CVE | Severity | Package | Installed | Fixed | Title |")
        details.append("| --- | --- | --- | --- | --- | --- |")
        for finding in item.findings:
            if shown >= max_details:
                break
            details.append(
                f"| {_cell(finding.vuln_id)} | {finding.severity} "
                f"| {_cell(finding.package)} | {_cell(finding.installed)} "
                f"| {_cell(finding.fixed) or '-'} | {_cell(finding.title)} |"
            )
            shown += 1
    lines += details
    if total_findings > max_details:
        lines += ["", f"Details truncated: {max_details} of {total_findings} findings listed."]

    errors = [item for item in scans if item.error]
    if errors:
        lines += ["", "### Images that could not be scanned", ""]
        lines += [f"- `{item.image}` ({item.ref.role}): {item.error}" for item in errors]
    return lines


def _table(scans: Sequence[Scan], options: Options) -> list[str]:
    """Render the report as an aligned table."""
    rows = [
        (
            item.ref.role,
            item.image,
            *(str(item.count(severity)) for severity in options.severities),
        )
        for item in scans
    ]
    headers = ("Role", "Image", *(severity.title() for severity in options.severities))
    widths = [max(len(row[index]) for row in (*rows, headers)) for index in range(len(headers))]
    lines = ["  ".join(header.ljust(width) for header, width in zip(headers, widths))]
    lines.append("  ".join("-" * width for width in widths))
    lines += [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows
    ]
    return lines


def _json(scans: Sequence[Scan]) -> list[str]:
    """Render the report as JSON."""
    payload = [
        {
            "role": item.ref.role,
            "image": item.image,
            "repo": item.ref.repo,
            "version": item.ref.version,
            "error": item.error,
            "findings": [finding.__dict__ for finding in item.findings],
        }
        for item in scans
    ]
    return [json.dumps(payload, indent=2)]


def render(scans: Sequence[Scan], options: Options, output: str, max_details: int) -> str:
    """Render the report in the requested format."""
    if output == "json":
        lines = _json(scans)
    elif output == "markdown":
        lines = _markdown(scans, options, max_details)
    else:
        lines = _table(scans, options)
        lines += ["", _summary(scans, options)]
        lines += [
            f"  {item.ref.role}: {item.error} ({item.image})" for item in scans if item.error
        ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="exit 1 when any image has findings"
    )
    parser.add_argument(
        "--severity",
        default="CRITICAL,HIGH",
        metavar="LIST",
        help="comma-separated severities to report (default CRITICAL,HIGH)",
    )
    parser.add_argument(
        "--include-unfixed",
        action="store_true",
        help="also report findings that have no fix available",
    )
    parser.add_argument(
        "--role", action="append", default=[], metavar="ROLE", help="limit to one role"
    )
    parser.add_argument("--format", choices=("table", "markdown", "json"), default="table")
    parser.add_argument(
        "--output", type=Path, metavar="PATH", help="write the report here instead of stdout"
    )
    parser.add_argument(
        "--jobs", type=int, default=4, metavar="N", help="images scanned in parallel (default 4)"
    )
    parser.add_argument(
        "--timeout", type=int, default=SCAN_TIMEOUT, metavar="SECONDS",
        help="timeout per image (default 600)",
    )
    parser.add_argument(
        "--max-details", type=int, default=40, help="findings listed in Markdown (default 40)"
    )
    parser.add_argument("--trivy", default="trivy", help="Trivy binary (default: trivy)")
    args = parser.parse_args(argv)

    severities = tuple(part.strip().upper() for part in args.severity.split(",") if part.strip())
    if not severities:
        parser.error("--severity needs at least one value")
    unknown = [severity for severity in severities if severity not in RANK]
    if unknown:
        parser.error(f"unknown severities: {', '.join(unknown)}")

    username = os.environ.get("DOCKERHUB_USERNAME", "").strip()
    password = os.environ.get("DOCKERHUB_TOKEN", "").strip()
    if username and not password:
        print("DOCKERHUB_USERNAME is set without DOCKERHUB_TOKEN; pulling anonymously.",
              file=sys.stderr)
        username = ""

    options = Options(
        binary=args.trivy,
        severities=severities,
        ignore_unfixed=not args.include_unfixed,
        jobs=args.jobs,
        timeout=args.timeout,
        username=username,
        password=password,
    )
    refs = inventory.discover(args.role)
    if not refs:
        print("No image references found.", file=sys.stderr)
        return 2
    if shutil.which(options.binary) is None:
        print(f"{options.binary} is not on PATH; install Trivy or pass --trivy.", file=sys.stderr)
        return 2

    error = prepare_database(options)
    if error:
        print(error, file=sys.stderr)
        return 2

    scans = scan_all(refs, options)
    report = render(scans, options, args.format, args.max_details)
    if args.output:
        args.output.write_text(report)
    else:
        print(report, end="")

    if all(item.error for item in scans):
        print("Every image failed to scan; see the report.", file=sys.stderr)
        return 2
    if args.check and any(item.findings for item in scans):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
