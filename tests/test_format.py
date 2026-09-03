import builtins
import importlib
import sys
import types
import pytest

from easydone import __version__
from easydone.storage import LoadStatus, CURRENT_SCHEMA_VERSION, LoadingResult


def _reload_format_module(monkeypatch, *, rich_available):
    """Import reload helper to simulate rich availability or absence."""
    if rich_available:
        rich_mod = types.ModuleType("rich")
        console_mod = types.ModuleType("rich.console")
        table_mod = types.ModuleType("rich.table")
        text_mod = types.ModuleType("rich.text")

        class FakeConsole:
            instances = []

            def __init__(self):
                self.rendered = []
                FakeConsole.instances.append(self)

            def print(self, obj):
                self.rendered.append(obj)

        class FakeTable:
            def __init__(self, show_header=True, header_style=None):
                self.show_header = show_header
                self.header_style = header_style
                self.columns = []
                self.rows = []

            def add_column(self, *args, **kwargs):
                self.columns.append(args[0])

            def add_row(self, *row):
                self.rows.append(row)

        class FakeText:
            def __init__(self, text, overflow=None, style=None):
                self.text = text
                self.overflow = overflow
                self.style = style

            def __str__(self):
                return self.text

        console_mod.Console = FakeConsole # type: ignore
        table_mod.Table = FakeTable # type: ignore
        text_mod.Text = FakeText # type: ignore

        monkeypatch.setitem(sys.modules, "rich", rich_mod)
        monkeypatch.setitem(sys.modules, "rich.console", console_mod)
        monkeypatch.setitem(sys.modules, "rich.table", table_mod)
        monkeypatch.setitem(sys.modules, "rich.text", text_mod)
    else:
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("rich"):
                raise ImportError("simulated missing rich")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    sys.modules.pop("easydone.format", None)
    return importlib.import_module("easydone.format")

# ================================================================
# print_table tests
# ================================================================

def test_print_table_uses_plain_text_fallback(monkeypatch, capsys):
    """When Rich is missing, output should use the plain tree-style table."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    tasks = {
        "123": {
            "description": "read a book",
            "status": "not-done",
            "priority": "low",
            "due": "2026-08-30",
            "created-at": "2026-08-22",
            "updated-at": None,
        }
    }

    format_module.print_table(tasks, ["123"])

    output = capsys.readouterr().out

    # Check for the tree-style table format
    assert "EASYDONE: Task Tracker" in output
    assert "ID: 123 ... \"read a book\"" in output
    assert "Priority: low" in output
    assert "Status: not-done" in output
    assert "Due: 2026-08-30" in output
    assert "Created at: 2026-08-22" in output
    assert "Updated at: -" in output

    # Test with no_dates=True
    format_module.print_table(tasks, ["123"], no_dates=True)

    output = capsys.readouterr().out

    assert "EASYDONE: Task Tracker" in output
    assert "ID: 123 ... \"read a book\"" in output
    assert "Priority: low" in output
    assert "Status: not-done" in output
    assert "Due" not in output
    assert "Created at" not in output
    assert "Updated at" not in output


def test_print_table_shows_no_tasks_message_plain_text(monkeypatch, capsys):
    """When there are no tasks to show, print a simple message."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    tasks = {}
    format_module.print_table(tasks, [])
    output = capsys.readouterr().out
    assert "No tasks to show." in output

    # Also test with tasks but empty ids list
    tasks = {"123": {"description": "test"}}
    format_module.print_table(tasks, [])
    output = capsys.readouterr().out
    assert "No tasks to show." in output


def test_print_table_uses_rich_when_available(monkeypatch):
    """When Rich is present, formatting should use the Rich table."""
    format_module = _reload_format_module(monkeypatch, rich_available=True)

    tasks = {
        "123": {
            "description": "read a book",
            "status": "done",
            "priority": "urgent",
            "due": "2026-08-30",
            "created-at": "2026-08-22",
            "updated-at": "2026-08-23",
        }
    }

    format_module.print_table(tasks, ["123"])

    assert format_module.RICH_AVAILABLE is True
    console_instances = sys.modules["rich.console"].Console.instances
    assert len(console_instances) == 1
    console = console_instances[0]
    assert len(console.rendered) == 1

    table = console.rendered[0]
    assert table.columns == ["ID", "Description", "Priority", "Status", "Due", "Created", "Updated"]
    assert len(table.rows) == 1
    row = table.rows[0]
    assert row[0] == "123"
    assert row[1].text == "read a book"
    assert row[2].text == "urgent"
    assert row[3].text == "done"
    assert row[4].text == "2026-08-30"
    assert row[5] == "2026-08-22"
    assert row[6] == "2026-08-23"


def test_print_table_uses_rich_with_no_dates(monkeypatch):
    """When Rich is present and no_dates=True, dates should be omitted."""
    format_module = _reload_format_module(monkeypatch, rich_available=True)

    tasks = {
        "123": {
            "description": "read a book",
            "status": "done",
            "priority": "urgent",
            "created-at": "2026-08-22",
            "updated-at": "2026-08-23",
        }
    }

    format_module.print_table(tasks, ["123"], no_dates=True)

    console_instances = sys.modules["rich.console"].Console.instances
    console = console_instances[-1]
    table = console.rendered[-1]
    assert table.columns == ["ID", "Description", "Priority", "Status"]


# ================================================================
# describe_load_result tests
# ================================================================

def test_describe_load_result_success(monkeypatch, capsys):
    """describe_load_result should print a success message."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.OK,
        file_path=None,
        schema_mismatch=False,
        app_mismatch=False,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Tasks loaded successfully." in output


def test_describe_load_result_missing(monkeypatch, capsys):
    """describe_load_result should print a missing file message."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.MISSING,
        file_path="/path/to/tasks.json", # type: ignore
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "/path/to/tasks.json does not exist" in output
    assert "Starting with an empty task list." in output


def test_describe_load_result_corrupted(monkeypatch, capsys):
    """describe_load_result should print a corruption warning."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.CORRUPTED,
        file_path="/path/to/tasks.json", # type: ignore
        backup_path="/path/to/tasks.corrupted-20260831.json", # type: ignore
        backup_exception=None,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Warning: /path/to/tasks.json is unreadable or malformed." in output
    assert "A copy was saved to /path/to/tasks.corrupted-20260831.json" in output


def test_describe_load_result_corrupted_without_backup(monkeypatch, capsys):
    """describe_load_result should handle corruption without backup."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    exc = PermissionError("Forbidden")
    result = LoadingResult(
        tasks={},
        status=LoadStatus.CORRUPTED,
        file_path="/path/to/tasks.json", # type: ignore
        backup_path=None,
        backup_exception=exc,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Warning: /path/to/tasks.json is unreadable or malformed." in output
    assert "Unable to save corrupted file: (Forbidden)" in output


def test_describe_load_result_schema_mismatch(monkeypatch, capsys):
    """describe_load_result should warn about schema mismatch."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.OK,
        found_schema_version=5,
        schema_mismatch=True,
        app_mismatch=False,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Warning: Found schema version 5" in output
    assert f"(app expects {CURRENT_SCHEMA_VERSION})" in output


def test_describe_load_result_app_mismatch(monkeypatch, capsys):
    """describe_load_result should warn about app version mismatch."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.OK,
        found_app_version="0.1.0",
        app_mismatch=True,
        schema_mismatch=False,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Warning: written by EasyDone 0.1.0" in output
    assert f"(running Easydone {__version__})" in output


def test_describe_load_result_both_mismatches(monkeypatch, capsys):
    """describe_load_result should show both schema and app mismatches."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = LoadingResult(
        tasks={},
        status=LoadStatus.OK,
        found_schema_version=5,
        found_app_version="0.1.0",
        schema_mismatch=True,
        app_mismatch=True,
    )

    format_module.describe_load_result(result)
    output = capsys.readouterr().out
    assert "Warning: Found schema version 5" in output
    assert f"(app expects {CURRENT_SCHEMA_VERSION})" in output
    assert "written by EasyDone 0.1.0" in output
    assert f"(running Easydone {__version__})" in output


# ================================================================
# report_backup tests
# ================================================================

def test_report_backup_success(monkeypatch, capsys):
    """report_backup should print success message."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    result = {"backup_path": "/path/to/backup.bak", "backup_exception": None}
    format_module.report_backup(result)
    output = capsys.readouterr().out
    assert "Backup succesfully done" in output


def test_report_backup_failure(monkeypatch, capsys):
    """report_backup should print failure warning."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    exc = PermissionError("Forbidden")
    result = {"backup_path": None, "backup_exception": exc}
    format_module.report_backup(result)
    output = capsys.readouterr().out
    assert "Warning: Couldn't backup (Forbidden)" in output


# ================================================================
# confirm_deletion tests
# ================================================================

def test_confirm_deletion_returns_true_on_y(monkeypatch):
    """confirm_deletion should return True when user types 'y'."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    monkeypatch.setattr("builtins.input", lambda: "y")

    result = format_module.confirm_deletion("123", "read a book")
    assert result is True


def test_confirm_deletion_returns_true_on_yes(monkeypatch):
    """confirm_deletion should accept 'yes' as confirmation."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    monkeypatch.setattr("builtins.input", lambda: "yes")

    result = format_module.confirm_deletion("123", "read a book")
    assert result is True


def test_confirm_deletion_returns_false_on_n(monkeypatch):
    """confirm_deletion should return False when user types 'n'."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    monkeypatch.setattr("builtins.input", lambda: "n")

    result = format_module.confirm_deletion("123", "read a book")
    assert result is False


def test_confirm_deletion_returns_false_on_no(monkeypatch):
    """confirm_deletion should accept 'no' as rejection."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    monkeypatch.setattr("builtins.input", lambda: "no")

    result = format_module.confirm_deletion("123", "read a book")
    assert result is False


def test_confirm_deletion_retries_on_invalid_input(monkeypatch):
    """confirm_deletion should retry on invalid input."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    inputs = iter(["invalid", "y"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    result = format_module.confirm_deletion("123", "read a book", max_attempts=3)
    assert result is True


def test_confirm_deletion_returns_false_after_max_attempts(monkeypatch):
    """confirm_deletion should return False after max attempts."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)
    inputs = iter(["invalid", "invalid", "invalid"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    result = format_module.confirm_deletion("123", "read a book", max_attempts=3)
    assert result is False


def test_confirm_deletion_raises_keyboardinterrupt(monkeypatch):
    """confirm_deletion should re-raise KeyboardInterrupt."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("builtins.input", interrupt)

    with pytest.raises(KeyboardInterrupt):
        format_module.confirm_deletion("123", "read a book")