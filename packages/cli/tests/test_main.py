from pathlib import Path

import pytest

from luibui_cli.main import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "luibui-scan" in capsys.readouterr().out


def test_help_without_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "luibui" in capsys.readouterr().out


def test_install_is_forwarded_to_luibui_install(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUIBUI_HOME", str(tmp_path))
    assert main(["install", "--liste"]) == 0
    assert "installiert" in capsys.readouterr().out.lower()
