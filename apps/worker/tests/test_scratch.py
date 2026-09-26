import uuid
from pathlib import Path

from luibui_worker.scratch import create_scratch, remove_scratch, sweep_orphans


def test_scratch_is_private(tmp_path: Path) -> None:
    path = create_scratch(tmp_path, uuid.uuid4())
    assert path.stat().st_mode & 0o777 == 0o700


def test_remove_handles_read_only_dirs(tmp_path: Path) -> None:
    path = create_scratch(tmp_path, uuid.uuid4())
    nested = path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "f").write_text("x")
    nested.chmod(0o500)
    (path / "a").chmod(0o500)
    remove_scratch(path)
    assert not path.exists()


def test_remove_does_not_follow_symlinks(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    path = create_scratch(tmp_path, uuid.uuid4())
    (path / "link").symlink_to(outside)
    remove_scratch(path)
    assert not path.exists()
    assert (outside / "keep.txt").read_text() == "keep"


def test_sweep_keeps_running_jobs(tmp_path: Path) -> None:
    running, orphan = uuid.uuid4(), uuid.uuid4()
    create_scratch(tmp_path, running)
    create_scratch(tmp_path, orphan)
    (tmp_path / "stray-file").write_text("x")
    removed = sweep_orphans(tmp_path, keep=[running])
    assert sorted(removed) == sorted([str(orphan), "stray-file"])
    assert [p.name for p in tmp_path.iterdir()] == [str(running)]


def test_sweep_spares_young_unknown_entries(tmp_path: Path) -> None:
    """The API writes an upload before its job row exists; such a directory must survive."""
    known, fresh = uuid.uuid4(), uuid.uuid4()
    create_scratch(tmp_path, known)
    create_scratch(tmp_path, fresh)
    removed = sweep_orphans(tmp_path, keep=[], known=[known], min_age_seconds=600)
    assert removed == [str(known)]
    assert sweep_orphans(tmp_path, keep=[], known=[], min_age_seconds=0) == [str(fresh)]


def test_create_scratch_takes_over_a_prepared_directory(tmp_path: Path) -> None:
    job = uuid.uuid4()
    prepared = tmp_path / str(job)
    prepared.mkdir(mode=0o755)
    (prepared / "SKILL.md").write_text("x")
    path = create_scratch(tmp_path, job)
    assert (path / "SKILL.md").exists()
    assert path.stat().st_mode & 0o777 == 0o700


def test_create_scratch_refuses_a_symlink(tmp_path: Path) -> None:
    import pytest

    job = uuid.uuid4()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / str(job)).symlink_to(tmp_path / "elsewhere")
    with pytest.raises(FileExistsError):
        create_scratch(tmp_path, job)
