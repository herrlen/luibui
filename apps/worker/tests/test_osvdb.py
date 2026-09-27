"""OSV database refresh: atomic replacement, broken downloads never destroy a working database."""

import io
import os
import time
import zipfile
from pathlib import Path

import pytest

from luibui_worker import osvdb


def zip_bytes(names: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in names:
            zf.writestr(n, "{}")
    return buf.getvalue()


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def serve(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> list[str]:
    calls: list[str] = []

    def urlopen(request: object, timeout: float) -> FakeResponse:
        calls.append(request.full_url)  # type: ignore[attr-defined]
        return FakeResponse(payload)

    monkeypatch.setattr(osvdb.urllib.request, "urlopen", urlopen)
    return calls


def test_refresh_downloads_stale_ecosystems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = serve(monkeypatch, zip_bytes(["GHSA-x.json"]))
    assert osvdb.refresh(tmp_path, max_age=3600, ecosystems=("PyPI", "npm")) == ["PyPI", "npm"]
    assert zipfile.is_zipfile(osvdb.target(tmp_path, "PyPI"))
    assert calls == [
        "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip",
        "https://osv-vulnerabilities.storage.googleapis.com/npm/all.zip",
    ]
    assert osvdb.refresh(tmp_path, max_age=3600, ecosystems=("PyPI", "npm")) == []  # fresh


def test_broken_download_keeps_the_old_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = osvdb.target(tmp_path, "PyPI")
    dest.parent.mkdir(parents=True)
    dest.write_bytes(zip_bytes(["old.json"]))
    old = time.time() - 10 * 86400
    os.utime(dest, (old, old))
    serve(monkeypatch, b"<html>kein zip</html>")
    assert osvdb.refresh(tmp_path, max_age=3600, ecosystems=("PyPI",)) == []
    with zipfile.ZipFile(dest) as zf:
        assert zf.namelist() == ["old.json"]
    assert not dest.with_suffix(".zip.part").exists()


def test_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, zip_bytes(["a.json"]) + b"x" * 2048)
    with pytest.raises(ValueError, match="größer"):
        osvdb.download("https://example.invalid/all.zip", tmp_path / "all.zip", max_bytes=1024)
    assert not (tmp_path / "all.zip").exists()


def test_only_https(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        osvdb.download("file:///etc/passwd", tmp_path / "all.zip")
