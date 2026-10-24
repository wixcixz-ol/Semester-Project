"""Configuration and validation for the file organizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

DEFAULT_CATEGORY_MAP: dict[str, tuple[str, ...]] = {
    "images": (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"),
    "documents": (".pdf", ".doc", ".docx", ".txt", ".odt"),
    "spreadsheets": (".xls", ".xlsx", ".csv", ".ods"),
    "archives": (".zip", ".rar", ".7z", ".tar", ".gz"),
    "audio": (".mp3", ".wav", ".flac", ".ogg"),
    "video": (".mp4", ".mov", ".avi", ".mkv", ".webm"),
    "code": (".py", ".js", ".ts", ".java", ".cpp", ".html", ".css"),
}


def _parse_bool(value: str, variable_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{variable_name} must be a boolean value")


@dataclass(frozen=True)
class OrganizerConfig:
    """Validated runtime settings for one organization operation."""

    source_dir: Path
    destination_dir: Path
    recursive: bool = False
    dry_run: bool = False
    conflict_policy: str = "skip"
    category_map: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: DEFAULT_CATEGORY_MAP.copy()
    )

    def validate(self) -> None:
        source = self.source_dir.expanduser().resolve()
        destination = self.destination_dir.expanduser().resolve()

        if not source.exists():
            raise ValueError(f"source directory does not exist: {source}")
        if not source.is_dir():
            raise ValueError(f"source path is not a directory: {source}")
        if source == destination:
            raise ValueError("destination directory must differ from source directory")
        if self.conflict_policy not in {"skip", "rename", "overwrite"}:
            raise ValueError("conflict policy must be skip, rename, or overwrite")
        if not self.category_map:
            raise ValueError("category map must contain at least one category")

        for category, extensions in self.category_map.items():
            if not category.strip():
                raise ValueError("category names cannot be empty")
            if not extensions:
                raise ValueError(f"category {category!r} has no extensions")
            if any(not extension.startswith(".") for extension in extensions):
                raise ValueError("category extensions must start with a dot")

    @classmethod
    def from_env(cls, *, validate: bool = True) -> "OrganizerConfig":
        """Create settings from environment variables with safe local defaults."""

        source = Path(os.getenv("ORGANIZER_SOURCE", "input")).expanduser()
        destination = Path(
            os.getenv("ORGANIZER_DESTINATION", str(source / "organized"))
        ).expanduser()
        config = cls(
            source_dir=source,
            destination_dir=destination,
            recursive=_parse_bool(
                os.getenv("ORGANIZER_RECURSIVE", "false"), "ORGANIZER_RECURSIVE"
            ),
            dry_run=_parse_bool(
                os.getenv("ORGANIZER_DRY_RUN", "false"), "ORGANIZER_DRY_RUN"
            ),
            conflict_policy=os.getenv("ORGANIZER_CONFLICT", "skip").strip().lower(),
        )
        if validate:
            config.validate()
        return config
