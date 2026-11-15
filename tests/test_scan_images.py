"""Unit tests for the report building in scan_images.py.

Trivy itself is never run: these cover parsing its JSON, the Docker Hub
credential scoping, and the Markdown budget that keeps the report under
GitHub's issue body limit.
"""
# pylint: disable=protected-access  # the leading-underscore helpers are the units under test
from pathlib import Path

import pytest

import check_image_versions as inventory
import scan_images as si


def _ref(role: str = "example", repo: str = "vendor/app", version: str = "1.2.3"
         ) -> inventory.ImageRef:
    return inventory.ImageRef(
        role=role,
        path=inventory.REPO_ROOT / "roles" / role / "defaults" / "main.yml",
        repo_key=f"{role}_image_name",
        version_key=f"{role}_image_version",
        repo=repo,
        version=version,
        line=7,
    )


def _finding(vuln_id: str = "CVE-2026-0001", severity: str = "HIGH",
             title: str = "bad thing") -> si.Finding:
    return si.Finding(vuln_id, "openssl", "3.0.0", "3.0.1", severity, title)


def test_parse_trivy_report() -> None:
    """Every vulnerability of every result becomes a finding; nulls are tolerated."""
    payload = {
        "Results": [
            {"Vulnerabilities": [
                {"VulnerabilityID": "CVE-1", "PkgName": "zlib", "InstalledVersion": "1",
                 "FixedVersion": "2", "Severity": "critical", "Title": "t"},
            ]},
            {"Vulnerabilities": None},
            {"Vulnerabilities": [{"VulnerabilityID": "CVE-2"}]},
        ]
    }
    findings = si._parse(payload)
    assert [(f.vuln_id, f.severity) for f in findings] == [("CVE-1", "CRITICAL"),
                                                           ("CVE-2", "UNKNOWN")]
    assert not si._parse({"Results": None})


def test_last_error_strips_the_log_prefix() -> None:
    """Only the message of Trivy's last stderr line is kept."""
    stderr = (
        "2026-11-14T10:00:00Z\tINFO\tstarting\n"
        "2026-11-14T10:00:01Z\tFATAL\tFatal error\tunable to find the specified image\n\n"
    )
    assert si._last_error(stderr) == "unable to find the specified image"
    assert si._last_error("") == ""


@pytest.mark.parametrize(
    ("repo", "scoped"),
    [("vendor/app", True), ("postgres", True), ("ghcr.io/vendor/app", False),
     ("lscr.io/linuxserver/app", False)],
)
def test_credentials_only_for_docker_hub(repo: str, scoped: bool) -> None:
    """The Docker Hub token is never sent to another registry."""
    options = si.Options(username="user", password="token")
    env = si._credentials(options, _ref(repo=repo))
    assert (env is not None) == scoped
    if env is not None:
        assert env["TRIVY_USERNAME"] == "user"
        assert env["TRIVY_PASSWORD"] == "token"


def test_credentials_absent_without_username() -> None:
    """Without credentials Trivy pulls anonymously with the inherited environment."""
    assert si._credentials(si.Options(), _ref()) is None


def test_cell_keeps_table_rows_intact() -> None:
    """Pipes are escaped and newlines folded, so a title cannot break the table."""
    assert si._cell("a|b\nc\r\n d") == "a\\|b c d"


def test_role_cell_links_to_the_pin() -> None:
    """With a source URL the role links to its pin line."""
    item = si.Scan(ref=_ref())
    assert si._role_cell(item, "") == "example"
    assert si._role_cell(item, "https://github.com/o/r/blob/abc/") == (
        "[example](https://github.com/o/r/blob/abc/roles/example/defaults/main.yml#L7)"
    )


def test_role_cell_outside_repo_is_plain() -> None:
    """Defaults outside the repository cannot be linked."""
    ref = _ref()
    ref.path = Path("/elsewhere/defaults/main.yml")
    assert si._role_cell(si.Scan(ref=ref), "https://x") == "example"


def test_summary_counts() -> None:
    """The summary counts affected images, findings per severity and errors."""
    options = si.Options()
    scans = [
        si.Scan(ref=_ref("a"), findings=[_finding(severity="CRITICAL"), _finding()]),
        si.Scan(ref=_ref("b")),
        si.Scan(ref=_ref("c"), error="boom"),
    ]
    assert si._summary(scans, options) == (
        "1 of 3 pinned images has findings (1 critical, 1 high); 1 could not be scanned."
    )
    assert si._summary([si.Scan(ref=_ref())], options) == "No findings in 1 pinned images."


def test_markdown_orders_worst_first_and_stamps() -> None:
    """The worst image leads the table and the stamp sits on top."""
    scans = [
        si.Scan(ref=_ref("mild"), findings=[_finding()]),
        si.Scan(ref=_ref("worst"), findings=[_finding(severity="CRITICAL")]),
    ]
    lines = si._markdown(scans, si.Options(), si.Layout(stamp="Scanned now"))
    assert lines[0] == "> Scanned now"
    rows = [line for line in lines if line.startswith("| ") and "vendor/app" in line]
    assert rows[0].startswith("| worst") and rows[1].startswith("| mild")


def test_markdown_stays_under_the_body_limit_with_errors() -> None:
    """Per-image blocks yield to the error list instead of overflowing the limit."""
    long_title = "x" * 400
    affected = [
        si.Scan(ref=_ref(f"role{i}"), findings=[_finding(f"CVE-{i}-{j}", title=long_title)
                                                for j in range(10)])
        for i in range(20)
    ]
    failed = [si.Scan(ref=_ref(f"broken{i}"), error=f"error {i} " + "y" * 80)
              for i in range(40)]
    limit = 20000
    text = "\n".join(si._markdown([*affected, *failed], si.Options(),
                                  si.Layout(body_limit=limit)))
    assert len(text) <= limit
    assert "images could not be scanned" in text
    assert "more images are in the full report" in text


def test_markdown_summary_only() -> None:
    """--details-per-image 0 leaves out the per-image blocks."""
    scans = [si.Scan(ref=_ref(), findings=[_finding()])]
    text = "\n".join(si._markdown(scans, si.Options(), si.Layout(per_image=0)))
    assert "<details>" not in text
    assert "Findings per image" not in text


def test_main_rejects_zero_jobs() -> None:
    """--jobs 0 is an argument error, not a ThreadPoolExecutor crash."""
    with pytest.raises(SystemExit) as excinfo:
        si.main(["--jobs", "0"])
    assert excinfo.value.code == 2


def test_scan_all_scans_a_shared_image_once(monkeypatch) -> None:
    """Two roles pinning the same image cost one scan, and both are reported."""
    calls: list[str] = []

    def fake_scan(ref: inventory.ImageRef, options: si.Options) -> si.Scan:
        del options
        calls.append(f"{ref.repo}:{ref.version}")
        return si.Scan(ref=ref, findings=[_finding()])

    monkeypatch.setattr(si, "scan", fake_scan)
    refs = [_ref("a", "postgres", "16"), _ref("b", "postgres", "16"), _ref("c", "redis", "7")]
    scans = si.scan_all(refs, si.Options(jobs=2))
    assert sorted(calls) == ["postgres:16", "redis:7"]
    assert [item.ref.role for item in scans] == ["a", "b", "c"]
    assert all(item.findings for item in scans)
