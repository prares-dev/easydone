# EasyDone Task Tracker

> A focused command-line task manager for turning a messy to-do list into a clear next action.

EasyDone is a small, dependency-free Python CLI for creating, updating, completing, deleting, and filtering tasks directly from your terminal. Tasks are saved as readable JSON, so your data stays simple, portable, and easy to inspect.

## Why EasyDone?

- Fast terminal-first workflow
- Statuses for work in motion: `not-done`, `in-progress`, and `done`
- Four priority levels: `low`, `normal`, `high`, and `urgent`
- Filter tasks by status, priority, or both
- Human-readable JSON storage with no database setup
- Small codebase that is easy to learn from and extend

## Project Structure

```text
easydone-task-tracker/
├── easydone/
│   ├── __main__.py   # Application entry point
│   ├── cli.py        # Argument parser and commands
│   ├── logic.py      # Task-management operations
│   └── storage.py    # JSON loading and saving
├── tests/
│   ├── logic_test.py
│   └── storage_test.py
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

On macOS or Linux, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

You can now run the application with:

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
easydone mark TASK_ID STATUS
```

Example:

```text
easydone mark 123 in-progress
```

### `delete`

Delete an existing task. EasyDone asks for confirmation unless `--forced` is used.

```text
easydone delete TASK_ID
easydone delete TASK_ID --forced
```

The short form is also available:

```text
easydone delete TASK_ID -f
```

### `list`

List all tasks or filter them by status and priority.

```text
easydone list [--status STATUS] [--priority PRIORITY]
```

When both filters are supplied, a task must match both of them.

## Data Storage

By default, EasyDone stores tasks in:

```text
data/tasks.json
```

The `data` directory is created automatically when the application saves its first task. The file uses a straightforward structure:

```json
{
	"123": {
		"description": "Finish project report",
		"status": "in-progress",
		"priority": "high"
	}
}
```

The storage path is relative to the directory where the command is run. Run EasyDone from the project directory when using the default location.

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
```

## License

This project is available under the license in [LICENSE](LICENSE).
