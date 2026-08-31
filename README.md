# easydone

> Your terminal-based task manager — simple, fast, and safe.

**easydone** is a lightweight CLI tool to keep your to‑do list in check.  
Create, update, mark done, delete, and filter tasks with a few keystrokes.  
All your data is stored as plain JSON, with **atomic writes, automatic backups, and corruption quarantine** so you never lose a task.

```shell
pip install easydone
```

---

## ✨ Why you'll like it

- **Instant workflow** – no mouse, no distractions.
- **Smart statuses**: `not-done`, `in-progress`, `done`.
- **Priority levels**: `low`, `normal`, `high`, `urgent`.
- **Filter** tasks by status, priority, or both.
- **Human‑readable JSON** – inspect your data anytime.
- **Bulletproof storage** – atomic writes, `.bak` backups, and quarantined corrupt files.
- **Beautiful output** with [Rich](https://github.com/Textualize/rich) – **optional**, falls back to plain text if not installed.
- **Clean architecture** – business logic separated from CLI, making the core testable and reusable.

---

## 📦 Installation

### Basic install (no extras)

```shell
pip install easydone
```

This installs the core tool with plain‑text output. Works perfectly for everyday use.

### With Rich (pretty output)

```shell
pip install easydone[pretty]
```

This installs [Rich](https://github.com/Textualize/rich) for colored tables, styled text, and a more polished terminal experience.

> 💡 **Note**: Rich is **completely optional**. If you install the basic version, easydone automatically falls back to clean plain‑text output. No functionality is lost – it just looks different.

---

## 🚀 Quick Start

```shell
# Create a task
easydone new "Read a book"

# Add details
easydone new "Finish report" --status in-progress --priority high

# List everything
easydone list

# Focus on urgent, unfinished tasks
easydone list --status not-done --priority urgent

# Mark complete
easydone mark 123 done

# Delete (with confirmation)
easydone delete 123

# Delete without confirmation
easydone delete 123 -f

# Delete multiple tasks
easydone delete 123 456 789 -f
```

---

## 📋 Command Reference

| Command | Description |
| :------ | :---------- |
| `easydone new DESCRIPTION [--status STATUS] [--priority PRIORITY]` | Create a task. Status defaults to `not-done`, priority to `low`. |
| `easydone update TASK_ID [--description NEW] [--priority NEW]` | Change description and/or priority. |
| `easydone mark TASK_ID new-status` | Set status to `not-done`, `in-progress`, or `done`. |
| `easydone delete TASK_ID [TASK_ID ...] [-f]` | Delete one or more tasks. Use `-f` to skip confirmation. |
| `easydone list [--status STATUS] [--priority PRIORITY] [--no-dates]` | Show tasks. Apply filters and hide dates if you like. |

> 💡 **Pro tip**: Delete multiple IDs at once: `easydone delete 123 456 789`. All IDs are validated before anything is removed – no partial deletions. Press `Ctrl+C` at any prompt to cancel the entire operation.

---

## 🛡️ Safety first

easydone takes care of your data:

- **Atomic writes** – a crash mid‑save never corrupts your file.
- **Automatic backups** – each save creates a `tasks.json.bak` in the same directory.
- **Corruption quarantine** – if a file is unreadable, it's copied to `tasks.corrupted-<timestamp>.json` instead of being discarded.

Your tasks live in a user‑specific folder:

| Platform | Location |
| :------- | :------- |
| Windows | `%APPDATA%\easydone\tasks.json` |
| macOS | `~/Library/Application Support/easydone/tasks.json` |
| Linux | `~/.local/share/easydone/tasks.json` |

You can override the storage path by setting the `EASYDONE_DATA_FILE` environment variable.

---

## 📁 Project Structure

```
easydone/
├── easydone/
│   ├── __init__.py   # Package metadata
│   ├── __main__.py   # Application entry point
│   ├── cli.py        # CLI interface (argparse, handlers, user prompts)
│   ├── logic.py      # Pure business logic (CRUD, validation, filtering)
│   ├── storage.py    # JSON persistence with atomic writes, backup & quarantine
│   └── format.py     # Output formatting (Rich / plain text)
├── tests/
│   ├── test_integration.py   # CLI + Logic integration tests
│   ├── test_storage.py     # Storage layer tests
│   └── test_format.py      # Output formatting tests
├── LICENSE
├── pyproject.toml
└── README.md
```

### Architecture Overview

- **`logic.py`** – Core business logic. Knows nothing about the CLI. Accepts only plain Python types (`str`, `list`, `bool`, etc.).
- **`cli.py`** – CLI interface. Parses arguments, extracts values, calls the manager, handles user prompts.
- **`storage.py`** – Persistence layer. Handles loading, saving, atomic writes, backups, and quarantine.
- **`format.py`** – Presentation layer. Renders tables and messages with Rich or plain‑text fallback.

This design makes the core reusable in other contexts (API, TUI, GUI) and easy to test.

---

## 🔧 Development

Install in editable mode with dev dependencies:

```shell
git clone https://github.com/prares-dev/easydone.git
cd easydone
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Run the complete test suite:

```shell
pytest
```

Run a specific test file:

```shell
pytest tests/test_integration.py
pytest tests/test_storage.py
pytest tests/test_format.py
```

### Test Structure

| Test File | What It Tests |
| :-------- | :------------ |
| `test_cli_logic.py` | CLI + Logic integration (argument parsing, handlers, user interaction, output) |
| `test_storage.py` | Storage layer (loading, saving, atomic writes, backups, quarantine) |
| `test_format.py` | Output formatting (Rich availability, plain‑text fallback) |

---

## 📄 License

MIT – see [LICENSE](LICENSE).

---

**Made with ❤️ by [Pedro Rosquete](https://github.com/prares-dev)** — feedback and contributions are always welcome!