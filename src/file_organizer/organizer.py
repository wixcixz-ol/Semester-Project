"""Core planning and execution logic for organizing files."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .config import OrganizerConfig


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    destination: Path
    category: str


@dataclass(frozen=True)
class OrganizationPlan:
    moves: tuple[PlannedMove, ...]
    skipped: int = 0


@dataclass(frozen=True)
class MoveResult:
    source: Path
    destination: Path
    status: str
    error: str | None = None


@dataclass(frozen=True)
class OrganizeReport:
    planned: int
    moved: int
    skipped: int
    failed: int
    dry_run: bool
    results: tuple[MoveResult, ...]


def _classify(path: Path, category_map: Mapping[str, tuple[str, ...]]) -> str:
    extension = path.suffix.lower()
    for category, extensions in category_map.items():
        if extension in {item.lower() for item in extensions}:
            return category
    return "other"


def _iter_source_files(source: Path, recursive: bool) -> Iterable[Path]:
    candidates = source.rglob("*") if recursive else source.iterdir()
    ordered = sorted(
        candidates,
        key=lambda path: (len(path.relative_to(source).parts), path.as_posix()),
    )
    for path in ordered:
        if path.is_file() and not path.is_symlink():
            yield path


def _next_available(path: Path, occupied: set[Path]) -> Path:
    stem, suffix = path.stem, path.suffix
    counter = 1
    candidate = path
    while candidate.resolve() in occupied or candidate.exists():
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        counter += 1
    return candidate


def build_plan(config: OrganizerConfig) -> OrganizationPlan:
    """Build a deterministic plan without changing the file system."""

    config.validate()
    source_root = config.source_dir.expanduser().resolve()
    destination_root = config.destination_dir.expanduser().resolve()
    occupied = {
        path.resolve()
        for path in destination_root.rglob("*")
        if path.is_file()
    } if destination_root.exists() else set()

    moves: list[PlannedMove] = []
    skipped = 0
    for source in _iter_source_files(source_root, config.recursive):
        resolved_source = source.resolve()
        if resolved_source.is_relative_to(destination_root):
            continue

        category = _classify(source, config.category_map)
        destination = destination_root / category / source.name
        resolved_destination = destination.resolve()

        if resolved_destination in occupied:
            if config.conflict_policy == "skip":
                skipped += 1
                continue
            if config.conflict_policy == "rename":
                destination = _next_available(destination, occupied)
            elif any(move.destination.resolve() == resolved_destination for move in moves):
                # Avoid losing an earlier planned file when two source folders share a name.
                destination = _next_available(destination, occupied)

        occupied.add(destination.resolve())
        moves.append(PlannedMove(source, destination, category))

    return OrganizationPlan(tuple(moves), skipped)


def execute_plan(plan: OrganizationPlan, dry_run: bool = False) -> tuple[MoveResult, ...]:
    """Execute a plan or return preview results when dry-run is enabled."""

    results: list[MoveResult] = []
    for move in plan.moves:
        if dry_run:
            results.append(MoveResult(move.source, move.destination, "planned"))
            continue

        try:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            if move.destination.exists():
                if move.destination.is_dir():
                    raise IsADirectoryError(move.destination)
                if move.destination.parent == move.source.parent:
                    results.append(MoveResult(move.source, move.destination, "skipped"))
                    continue
                move.destination.unlink()
            shutil.move(str(move.source), str(move.destination))
            results.append(MoveResult(move.source, move.destination, "moved"))
        except OSError as error:
            results.append(
                MoveResult(move.source, move.destination, "failed", str(error))
            )
    return tuple(results)


def organize(config: OrganizerConfig) -> OrganizeReport:
    plan = build_plan(config)
    results = execute_plan(plan, config.dry_run)
    moved = sum(result.status == "moved" for result in results)
    failed = sum(result.status == "failed" for result in results)
    skipped = plan.skipped + sum(result.status == "skipped" for result in results)
    return OrganizeReport(
        planned=len(plan.moves),
        moved=moved,
        skipped=skipped,
        failed=failed,
        dry_run=config.dry_run,
        results=results,
    )
