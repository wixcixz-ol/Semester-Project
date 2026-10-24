from datetime import datetime, timezone
from pathlib import Path

import pytest

from file_organizer.config import OrganizerConfig
from file_organizer.history import HistoryStore
from file_organizer.organizer import organize


def test_history_store_persists_report_and_moves(tmp_path: Path) -> None:
    source = tmp_path / "input"
    destination = tmp_path / "organized"
    database = tmp_path / "state" / "history.sqlite3"
    source.mkdir()
    (source / "notes.txt").write_text("notes")

    report = organize(OrganizerConfig(source, destination))
    started = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    with HistoryStore(database) as store:
        run_id = store.record_report(
            report,
            started_at=started,
            completed_at=started,
        )
        run = store.get_run(run_id)
        moves = store.list_moves(run_id)

    assert run is not None
    assert run.run_id == run_id
    assert run.moved == 1
    assert run.started_at == started
    assert len(moves) == 1
    assert moves[0].status == "moved"
    assert moves[0].source.name == "notes.txt"


def test_history_store_lists_newest_runs_first(tmp_path: Path) -> None:
    source = tmp_path / "input"
    source.mkdir()
    report = organize(
        OrganizerConfig(source, tmp_path / "organized", dry_run=True)
    )

    with HistoryStore(tmp_path / "history.sqlite3") as store:
        first = store.record_report(report)
        second = store.record_report(report)
        runs = store.list_runs(limit=2)

    assert [run.run_id for run in runs] == [second, first]
    assert all(run.dry_run for run in runs)


def test_history_store_rejects_invalid_limit(tmp_path: Path) -> None:
    with HistoryStore(tmp_path / "history.sqlite3") as store:
        with pytest.raises(ValueError, match="at least 1"):
            store.list_runs(limit=0)
