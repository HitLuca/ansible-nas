"""Run each role's molecule scenario as a pytest test, so VS Code's Testing
panel can run all roles or just a selection. Mirrors the CI step:
    cd roles/<role> && molecule --base-config ../../tests/molecule/base.yml test

Roles start their containers through the host's docker socket, so they are
siblings of the molecule instance and `molecule destroy` never removes them.
After each test we remove the containers that appeared during it AND whose
name is a *_container_name from the role's defaults. Any other new container
(e.g. one you started yourself meanwhile) is left alone and reported.
"""
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
ROLES = sorted(p.parent for p in (REPO / "roles").glob("*/molecule"))


def _containers() -> dict[str, str]:
    """Return {container id: name} for every container, running or not."""
    out = subprocess.run(
        ["docker", "ps", "-a", "--no-trunc", "--format", "{{.ID}} {{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return dict(line.split(" ", 1) for line in out.splitlines() if line)


def _container_names(role: Path) -> set[str]:
    """Literal *_container_name values from the role's defaults."""
    defaults = yaml.safe_load((role / "defaults" / "main.yml").read_text()) or {}
    return {
        v
        for k, v in defaults.items()
        if k.endswith("_container_name") and isinstance(v, str) and "{{" not in v
    }


@pytest.mark.parametrize("role", ROLES, ids=lambda p: p.name)
def test_role(role: Path):
    before = set(_containers())
    # Use the tools from the interpreter running pytest (the uv environment).
    bin_dir = str(Path(sys.executable).parent)
    env = {
        **os.environ,
        "PATH": bin_dir + os.pathsep + os.environ.get("PATH", ""),
        "PY_COLORS": "0",
        "ANSIBLE_FORCE_COLOR": "0",
    }
    try:
        result = subprocess.run(
            ["molecule", "--base-config", "../../tests/molecule/base.yml", "test"],
            cwd=role,
            env=env,
            capture_output=True,
            text=True,
        )
    finally:
        mine = _container_names(role)
        new = {i: n for i, n in _containers().items() if i not in before}
        ours = [i for i, n in new.items() if n in mine]
        if ours:
            subprocess.run(["docker", "rm", "-f", *ours], capture_output=True)
        others = sorted(n for i, n in new.items() if i not in ours)
        if others:
            warnings.warn(f"left alone (not in {role.name} defaults): {others}")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-3000:]
