from pathlib import Path

import pytest

from file_organizer.config import OrganizerConfig
from file_organizer.organizer import build_plan, organize


def make_config(source: Path, destination: Path, **kwargs) -> OrganizerConfig:
    return OrganizerConfig(source, destination, **kwargs)


def test_plan_classifies_files_and_excludes_destination(tmp_path: Path) -> None:
    source = tmp_path / "input"
    destination = source / "organized"
    source.mkdir()
    destination.mkdir()
    (source / "photo.JPG").write_text("image")
    (source / "notes.txt").write_text("notes")
    (destination / "old.pdf").write_text("already organized")

    plan = build_plan(make_config(source, destination, recursive=True))

    assert [(move.source.name, move.category) for move in plan.moves] == [
        ("notes.txt", "documents"),
        ("photo.JPG", "images"),
    ]
    assert plan.skipped == 0


def test_dry_run_does_not_move_files(tmp_path: Path) -> None:
    source = tmp_path / "input"
    destination = tmp_path / "organized"
    source.mkdir()
    (source / "report.pdf").write_text("report")

    report = organize(make_config(source, destination, dry_run=True))

    assert report.planned == 1
    assert report.moved == 0
    assert (source / "report.pdf").exists()
    assert not destination.exists()


def test_rename_policy_keeps_colliding_files(tmp_path: Path) -> None:
    source = tmp_path / "input"
    destination = tmp_path / "organized"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (source / "same.txt").write_text("first")
    (nested / "same.txt").write_text("second")

    report = organize(
        make_config(source, destination, recursive=True, conflict_policy="rename")
    )

    assert report.moved == 2
    assert (destination / "documents" / "same.txt").read_text() == "first"
    assert (destination / "documents" / "same_1.txt").read_text() == "second"


def test_skip_policy_reports_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "input"
    destination = tmp_path / "organized"
    source.mkdir()
    target = destination / "documents"
    target.mkdir(parents=True)
    (source / "notes.txt").write_text("new")
    (target / "notes.txt").write_text("old")

    report = organize(make_config(source, destination, conflict_policy="skip"))

    assert report.planned == 0
    assert report.skipped == 1
    assert (source / "notes.txt").exists()


def test_source_must_exist_and_destination_must_differ(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="does not exist"):
        OrganizerConfig(missing, tmp_path / "organized").validate()

    source = tmp_path / "input"
    source.mkdir()
    with pytest.raises(ValueError, match="must differ"):
        OrganizerConfig(source, source).validate()
