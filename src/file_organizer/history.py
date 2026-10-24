from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .organizer import OrganizeReport


class HistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrganizationRun:
    run_id: int
    started_at: datetime
    completed_at: datetime
    dry_run: bool
    planned: int
    moved: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class MoveRecord:
    move_id: int
    run_id: int
    source: Path
    destination: Path
    status: str
    error: str | None


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class HistoryStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).expanduser()
        if self._database_path.exists() and self._database_path.is_dir():
            raise ValueError(
                f"history database path is a directory: {self._database_path}"
            )
        if self._database_path.parent != Path("."):
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(str(self._database_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 5000")
            self._initialize_schema()
        except sqlite3.Error as error:
            raise HistoryError(
                f"could not open history database {self._database_path}: {error}"
            ) from error

    @classmethod
    def from_env(cls) -> "HistoryStore":
        raw_path = os.getenv(
            "ORGANIZER_HISTORY_DB", "organizer_history.sqlite3"
        ).strip()
        if not raw_path:
            raise ValueError("ORGANIZER_HISTORY_DB cannot be empty")
        return cls(Path(raw_path))

    @property
    def database_path(self) -> Path:
        return self._database_path

    def _ensure_open(self) -> sqlite3.Connection:
        connection = getattr(self, "_connection", None)
        if connection is None:
            raise HistoryError("history store is closed")
        return connection

    def _initialize_schema(self) -> None:
        connection = self._ensure_open()
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS organization_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                dry_run INTEGER NOT NULL CHECK (dry_run IN (0, 1)),
                planned INTEGER NOT NULL CHECK (planned >= 0),
                moved INTEGER NOT NULL CHECK (moved >= 0),
                skipped INTEGER NOT NULL CHECK (skipped >= 0),
                failed INTEGER NOT NULL CHECK (failed >= 0)
            );
            CREATE TABLE IF NOT EXISTS file_moves (
                move_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES organization_runs(run_id)
                    ON DELETE CASCADE,
                source TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('planned', 'moved', 'skipped', 'failed')
                ),
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_file_moves_run_id
                ON file_moves(run_id);
            """
        )
        connection.commit()

    def record_report(
        self,
        report: OrganizeReport,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> int:
        connection = self._ensure_open()
        started = started_at or datetime.now(timezone.utc)
        completed = completed_at or datetime.now(timezone.utc)
        try:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO organization_runs
                        (started_at, completed_at, dry_run, planned, moved, skipped, failed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _serialize_datetime(started),
                        _serialize_datetime(completed),
                        int(report.dry_run),
                        report.planned,
                        report.moved,
                        report.skipped,
                        report.failed,
                    ),
                )
                run_id = cursor.lastrowid
                if run_id is None:
                    raise HistoryError("database did not return a run ID")
                connection.executemany(
                    """
                    INSERT INTO file_moves
                        (run_id, source, destination, status, error)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            run_id,
                            str(result.source),
                            str(result.destination),
                            result.status,
                            result.error,
                        )
                        for result in report.results
                    ),
                )
                return int(run_id)
        except sqlite3.Error as error:
            raise HistoryError(
                f"could not record organization report: {error}"
            ) from error

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")

    def list_runs(self, *, limit: int = 50) -> tuple[OrganizationRun, ...]:
        self._validate_limit(limit)
        connection = self._ensure_open()
        try:
            rows = connection.execute(
                """
                SELECT run_id, started_at, completed_at, dry_run,
                       planned, moved, skipped, failed
                FROM organization_runs
                ORDER BY run_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.Error as error:
            raise HistoryError(
                f"could not list organization runs: {error}"
            ) from error
        return tuple(self._run_from_row(row) for row in rows)

    def get_run(self, run_id: int) -> OrganizationRun | None:
        connection = self._ensure_open()
        try:
            row = connection.execute(
                """
                SELECT run_id, started_at, completed_at, dry_run,
                       planned, moved, skipped, failed
                FROM organization_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        except sqlite3.Error as error:
            raise HistoryError(
                f"could not load organization run {run_id}: {error}"
            ) from error
        return self._run_from_row(row) if row is not None else None

    def list_moves(self, run_id: int) -> tuple[MoveRecord, ...]:
        connection = self._ensure_open()
        try:
            rows = connection.execute(
                """
                SELECT move_id, run_id, source, destination, status, error
                FROM file_moves
                WHERE run_id = ?
                ORDER BY move_id
                """,
                (run_id,),
            ).fetchall()
        except sqlite3.Error as error:
            raise HistoryError(
                f"could not list moves for run {run_id}: {error}"
            ) from error
        return tuple(self._move_from_row(row) for row in rows)

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> OrganizationRun:
        return OrganizationRun(
            run_id=int(row["run_id"]),
            started_at=_parse_datetime(row["started_at"]),
            completed_at=_parse_datetime(row["completed_at"]),
            dry_run=bool(row["dry_run"]),
            planned=int(row["planned"]),
            moved=int(row["moved"]),
            skipped=int(row["skipped"]),
            failed=int(row["failed"]),
        )

    @staticmethod
    def _move_from_row(row: sqlite3.Row) -> MoveRecord:
        return MoveRecord(
            move_id=int(row["move_id"]),
            run_id=int(row["run_id"]),
            source=Path(row["source"]),
            destination=Path(row["destination"]),
            status=str(row["status"]),
            error=row["error"],
        )

    def close(self) -> None:
        connection = getattr(self, "_connection", None)
        if connection is not None:
            connection.close()
            self._connection = None

    def __enter__(self) -> "HistoryStore":
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
