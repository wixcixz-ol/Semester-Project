# Smart File Organizer

## Nazov projektu / Project title

Smart File Organizer

## Kratky popis / Short description

Smart File Organizer is a Python command-line application that groups files into folders such as `images`, `documents`, `archives`, and `other` based on their extensions.

## Co projekt riesi / Problem being solved

Downloaded files and study materials often accumulate in one folder. Manually sorting them is repetitive and makes it easy to overwrite or forget files. The application creates a repeatable, configurable workflow that can first preview changes and then perform them.

The selected topic is a file-processing and automation utility because it has a meaningful core task, clear input validation, conflict handling, and room for later history and analysis features.

## Aktualne funkcie / Current functionality

- classify files into category folders using a configurable extension map;
- process only one directory or include subdirectories;
- support `skip`, `rename`, and `overwrite` conflict policies;
- support a safe `--dry-run` preview;
- read default paths and options from environment variables;
- expose the same core logic as importable Python functions;
- validate paths and configuration and report failed moves;
- test planning, dry-run behavior, conflicts, and invalid input.

## Planovane funkcie / Planned functionality

- SQLite history of organization runs and moved files;
- a small Tkinter review window for approving a plan;
- CSV/JSON reports and pandas-based statistics about file types and storage;
- undo for the last organization run;
- optional scheduled automation and richer user-defined rules;
- final user and technical documentation plus a presentation.

## Pouzite alebo planovane technologicke oblasti / Used or planned technology areas

1. **Scripting and automation:** `pathlib` and `shutil` discover and move files while remaining portable across operating systems.
2. **User interface:** `argparse` provides a reproducible CLI suitable for repeated use and automation.
3. **Configuration and structured data:** environment variables and a custom category map separate user settings from application logic; SQLite and JSON reports are planned for the final version.
4. **Testing:** `pytest` verifies the core behavior and protects the file-system operations from regressions.

## Postup spustenia aktualneho MVP / How to run the current MVP

Requirements: Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Preview a run:

```powershell
python -m file_organizer --source .\input --destination .\organized --recursive --dry-run
```

Execute the same plan by removing `--dry-run`:

```powershell
python -m file_organizer --source .\input --destination .\organized --recursive --conflict rename
```

The installed command `file-organizer` is also available after installation. Copy `.env.example` to `.env` and export the variables manually if environment-based defaults are preferred. The current MVP does not load `.env` automatically, so no hidden dependency is required.

Run tests:

```powershell
python -m pytest
```

## Struktura projektu / Project structure

```text
src/file_organizer/
  cli.py          command-line parsing and output
  config.py       settings, defaults, and validation
  organizer.py    planning and file operations
tests/            automated tests for the MVP
docs/             architecture and milestone notes
```

## Plan pred finalnou verziou / Plan before the final version

The Week 6 MVP intentionally stops after the first runnable core. The next milestone is to persist operation history in SQLite, then add an approval-oriented GUI and reports. The final version will also expand tests for error recovery, document the complete configuration format, and include a presentation of the architecture and demo workflow.

