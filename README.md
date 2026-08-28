# EasyDone Task Tracker

> A focused command-line task manager for turning a messy to-do list into a clear next action.

EasyDone is a lightweight Python CLI for creating, updating, completing, deleting, and filtering tasks directly from your terminal. Tasks are saved as readable JSON, and the storage layer now includes **automatic backups, corruption quarantine, and atomic writes** to keep your data safe.

## Why EasyDone?

- Fast terminal-first workflow  
- Statuses for work in motion: `not-done`, `in-progress`, and `done`  
- Four priority levels: `low`, `normal`, `high`, and `urgent`  
- Filter tasks by status, priority, or both  
- Human-readable JSON storage with no database setup  
- **Bulletproof data handling**: atomic writes, automatic `.bak` backups, and quarantine of corrupted files  
- Pretty terminal output with [Rich](https://github.com/Textualize/rich) (falls back to plain text if unavailable)

## Project Structure

```text
easydone-task-tracker/
├── easydone/
│   ├── __init__.py   # Package metadata (version, etc.)
│   ├── __main__.py   # Application entry point
│   ├── cli.py        # Argument parser and command dispatch
│   ├── logic.py      # Task-management operations
│   ├── storage.py    # JSON loading/saving with backup & quarantine
│   └── format.py     # Output formatting (Rich / plain)
├── tests/
│   ├── test_cli.py
│   ├── test_logic.py
│   ├── test_storage.py
│   └── test_format.py
├── LICENSE
├── pyproject.toml    # Packaging and pytest configuration
└── README.md
```

## Quick Start

### Requirements

- Python 3.9 or newer  
- Windows PowerShell, macOS, or Linux terminal

From the project root, create a virtual environment and install `EasyDone` in editable mode:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Or install directly from PyPI:

```powershell
py -m pip install easydone-task-tracker
```

You can now run the application:

```text
easydone
```

To see all available commands:

```text
easydone --help
```

## Everyday Workflow

Create a task:

```text
easydone new "Read a book"
```

Create a task with a status and priority:

```text
easydone new "Finish project report" --status in-progress --priority high
```

List everything:

```text
easydone list
```

Focus on urgent unfinished work:

```text
easydone list --status not-done --priority urgent
```

Mark a task as complete:

```text
easydone mark 123 done
```

## Command Reference

### `new`

Create a task. The description is required.

```text
easydone new DESCRIPTION [--status STATUS] [--priority PRIORITY]
```

Options:

- `-s`, `--status`: `not-done`, `done`, or `in-progress`; defaults to `not-done`
- `-p`, `--priority`: `low`, `normal`, `high`, or `urgent`; defaults to `low`

### `update`

Change the description and/or priority of an existing task.  
The `--priority` option now validates against the four allowed values.

```text
easydone update TASK_ID [--description NEW_DESCRIPTION] [--priority NEW_PRIORITY]
```

Examples:

```text
easydone update 123 --description "Read a novel"
easydone update 123 --priority high
```

### `mark`

Change the status of an existing task.

```text
easydone mark TASK_ID new-status
```

### `delete`

Delete one or more existing tasks. EasyDone asks for confirmation for each ID unless `-f` or `--forced` is used.

```text
easydone delete TASK_ID [TASK_ID ...]
easydone delete TASK_ID [TASK_ID ...] --forced
```

If you supply multiple IDs, all of them are validated before any deletion occurs. If any ID is invalid, the entire operation is aborted and no tasks are removed.

### `list`

List all tasks or filter them by status and priority. You can omit dates with the `--no-dates` option.

```text
easydone list [--status STATUS] [--priority PRIORITY] [--no-dates]
```

When both filters are supplied, a task must match both of them.

## Data Storage

EasyDone stores task data in a user‑scoped application directory so it does not depend on where the command is launched from.

- **Windows**: `%APPDATA%\easydone-task-tracker\tasks.json`
- **macOS**: `~/Library/Application Support/easydone-task-tracker/tasks.json`
- **Linux**: `~/.local/share/easydone-task-tracker/tasks.json`

The app writes a small metadata wrapper with the file schema version and the version of EasyDone that saved it. This makes future upgrades safer and compatibility warnings explicit.

```json
{
    "schema_version": 1,
    "app_version": "0.2.0",
    "saved_at": "2026-08-28",
    "tasks": {
        "123": {
            "description": "Finish project report",
            "status": "in-progress",
            "priority": "high",
            "created-at": "2026-08-28",
            "updated-at": null
        }
    }
}
```

### Safety & Recovery

EasyDone now protects your data in three ways:

1. **Atomic writes**: Every save writes to a temporary file first, then swaps it atomically. A crash mid‑write never leaves a half‑written file.
2. **Automatic backups**: Before every save, the current `tasks.json` is copied to `tasks.json.bak`. If something goes wrong, you can restore from this backup.
3. **Corruption quarantine**: If EasyDone encounters an unreadable or malformed file on load, it copies that file to `tasks.corrupted-<timestamp>.json` instead of discarding it. You can inspect the quarantined file and recover data manually.

If an older file is found (different schema or app version), EasyDone still loads it but prints a detailed warning so you can review the data before saving again.

## Development

Install the development dependency group:

```text
py -m pip install -e ".[dev]"
```

Run the complete test suite:

```text
py -m pytest
```

Run a specific test module:

```text
py -m pytest tests/logic_test.py
py -m pytest tests/storage_test.py
py -m pytest tests/format_test.py
```

## License

This project is available under the license in [LICENSE](LICENSE).