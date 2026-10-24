"""Command-line interface for the Smart File Organizer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import DEFAULT_CATEGORY_MAP, OrganizerConfig
from .organizer import organize


def _parse_category_map(value: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for item in value.split(","):
        if ":" not in item:
            raise argparse.ArgumentTypeError(
                "category map entries must use category:ext1|ext2"
            )
        category, raw_extensions = item.split(":", 1)
        category = category.strip()
        extensions = tuple(
            extension.strip().lower()
            if extension.strip().startswith(".")
            else f".{extension.strip().lower()}"
            for extension in raw_extensions.split("|")
            if extension.strip()
        )
        if not category or not extensions:
            raise argparse.ArgumentTypeError("category map entries cannot be empty")
        if category in result:
            raise argparse.ArgumentTypeError(f"duplicate category: {category}")
        result[category] = extensions
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Plan and organize files into category folders.",
    )
    parser.add_argument("--source", type=Path, help="directory containing files")
    parser.add_argument("--destination", type=Path, help="directory for category folders")
    parser.add_argument("--recursive", action="store_true", help="include subdirectories")
    parser.add_argument("--dry-run", action="store_true", help="preview changes only")
    parser.add_argument(
        "--conflict",
        choices=("skip", "rename", "overwrite"),
        help="how to handle an existing destination file",
    )
    parser.add_argument(
        "--category-map",
        type=_parse_category_map,
        help="custom mapping such as images:jpg|png,code:py|js",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _make_config(args: argparse.Namespace) -> OrganizerConfig:
    # Explicit CLI paths must work even when the optional default input folder is absent.
    base = OrganizerConfig.from_env(validate=False)
    return OrganizerConfig(
        source_dir=args.source or base.source_dir,
        destination_dir=args.destination or base.destination_dir,
        recursive=args.recursive or base.recursive,
        dry_run=args.dry_run or base.dry_run,
        conflict_policy=args.conflict or base.conflict_policy,
        category_map=args.category_map or base.category_map or DEFAULT_CATEGORY_MAP,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = organize(_make_config(args))
    except ValueError as error:
        parser.error(str(error))

    mode = "DRY RUN" if report.dry_run else "COMPLETED"
    print(f"{mode}: planned={report.planned} moved={report.moved} "
          f"skipped={report.skipped} failed={report.failed}")
    for result in report.results:
        if result.status == "failed":
            print(f"FAILED: {result.source} -> {result.destination}: {result.error}")
    return 1 if report.failed else 0
