# MVP Architecture

The application is split into three small layers:

```text
CLI (cli.py)
  -> configuration (config.py)
  -> planning and execution (organizer.py)
  -> local file system
```

`OrganizerConfig` owns input validation and environment defaults. `build_plan` is side-effect free apart from reading directory metadata, which makes the dry-run mode and tests straightforward. `execute_plan` is the only component that moves or deletes files. The CLI translates arguments into a configuration, calls the service layer, and formats a short result.

The MVP deliberately does not add a GUI yet. The `OrganizeReport` and
`MoveResult` data objects give the next milestones a stable place to add
undo information and a review interface.

`HistoryStore` provides the SQLite boundary without coupling storage to the
CLI. It creates the schema, records a report and its move results in one
transaction, and exposes typed queries for recent runs and individual moves.
