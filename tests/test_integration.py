"""Integration tests for CLI + Logic layers combined.

This module tests how the CLI interface interacts with the task manager.
We use pytest fixtures that might look unfamiliar, so here's what they do:

┌─────────────────────────────────────────────────────────────────────┐
│ FIXTURES: The "tools" pytest gives us                               │
├─────────────────────────────────────────────────────────────────────┤
│ capsys      - Captures everything printed to the terminal.          │
│               Use it to check what your print() statements          │
│               or console.print() calls actually output.             │
│               Example: output = capsys.readouterr().out             │
│                                                                     │
│ monkeypatch - Temporarily replaces parts of Python during test.     │
│               Use it to:                                            │
│               - Simulate user input (input() → "y")                 │
│               - Control environment variables                       │
│               - Replace functions with mock versions                │
│               Example: monkeypatch.setattr("builtins.input", ...)   │
│                                                                     │
│ tmp_path    - Creates a temporary directory that's cleaned up.      │
│               Use it for file operations without affecting          │
│               your real data.                                       │
│               Example: json_file = tmp_path / "tasks.json"          │
└─────────────────────────────────────────────────────────────────────┘
These tests verify that:
- The CLI parser extracts arguments correctly
- Handlers call the manager methods with the right parameters
- User interaction (confirmation) works as expected
- Return values (mutation flags) are correct
- Errors are caught and displayed properly
"""

from datetime import datetime, timedelta

import pytest

from easydone.cli import Parser
from easydone.logic import TasksManager
from easydone import __version__


@pytest.fixture
def manager():
    """Return a TasksManager with 3 predefined tasks for testing.

    These tasks are used in most tests to simulate realistic data.
    """
    date = datetime(2026, 9, 1)
    return TasksManager({
        "123": {
            "description": "read a book",
            "status": "not-done",
            "priority": "low",
            "created-at": str(date + timedelta(days=3)).split(" ")[0],
            "updated-at": str(date + timedelta(days=9)).split(" ")[0]
        },
        "456": {
            "description": "write code",
            "status": "done",
            "priority": "normal",
            "created-at": str(date).split(" ")[0],
            "updated-at": str(date + timedelta(days=4)).split(" ")[0]
        },
        "111": {
            "description": "go supermarket",
            "status": "in-progress",
            "priority": "urgent",
            "created-at": str(date + timedelta(days=5)).split(" ")[0],
            "updated-at": str(date + timedelta(days=7)).split(" ")[0]
        }
    })

@pytest.fixture
def empty_manager():
    """Return a TasksManager with no tasks (fresh start)."""
    return TasksManager({})

@pytest.fixture
def parser(manager):
    """Return a Parser instance with predefined tasks."""
    return Parser(manager)

@pytest.fixture
def empty_parser(empty_manager):
    """Return a Parser instance with no tasks."""
    return Parser(empty_manager)


# ============================================================
# 1. VERSION / HELP
# ============================================================

def test_version_output(empty_parser, capsys):
    """Running -v or --version should output the correct version."""
    # capsys captures what's printed to stdout/stderr
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(['-v'])
        output = capsys.readouterr().out
        assert __version__ in output

    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(['--version'])
        output = capsys.readouterr().out
        assert __version__ in output


def test_no_args_shows_help(empty_parser, capsys, monkeypatch):
    """Running 'easydone' with no args should print help."""
    # monkeypatch temporarily replaces sys.argv so the app thinks
    # the user just typed "easydone" with no arguments
    monkeypatch.setattr("sys.argv", ["easydone"])
    result = empty_parser.start_parsing()
    assert result is False

    # capsys captures what was printed so we can check it
    output = capsys.readouterr().out
    assert "usage" in output.lower() or "help" in output.lower() or "actions" in output.lower()


# ============================================================
# 2. ARGUMENT PARSING (our configuration, not argparse itself)
# ============================================================

def test_new_parser_has_correct_defaults(empty_parser):
    """Defaults are set correctly in our parser config."""
    args = empty_parser.main_parser.parse_args(["new", "test"])
    assert args.status == "not-done"
    assert args.priority == "low"


def test_new_parser_accepts_valid_choices(empty_parser):
    """Parser accepts valid status and priority choices."""
    args = empty_parser.main_parser.parse_args([
        "new", "test", "--status", "done", "--priority", "high"
    ])
    assert args.status == "done"
    assert args.priority == "high"


def test_new_parser_rejects_invalid_status(empty_parser):
    """Parser rejects invalid status choices."""
    # argparse raises SystemExit when it encounters invalid input
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args([
            "new", "test", "--status", "invalid"
        ])


def test_new_parser_rejects_invalid_priority(empty_parser):
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args([
            "new", "test", "--priority", "invalid"
        ])


def test_update_parser_accepts_valid_priority(empty_parser):
    args = empty_parser.main_parser.parse_args([
        "update", "123", "--priority", "high"
    ])
    assert args.priority == "high"


def test_update_parser_rejects_invalid_priority(empty_parser):
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args([
            "update", "123", "--priority", "invalid"
        ])


def test_delete_parser_handles_multiple_ids(empty_parser):
    args = empty_parser.main_parser.parse_args(["delete", "123", "456", "789"])
    assert args.ids == ["123", "456", "789"]
    assert args.forced is False


def test_delete_parser_handles_forced_flag(empty_parser):
    args = empty_parser.main_parser.parse_args(["delete", "123", "-f"])
    assert args.forced is True


def test_list_parser_no_dates_default_false(empty_parser):
    args = empty_parser.main_parser.parse_args(["list"])
    assert args.no_dates is False


def test_list_parser_handles_no_dates_flag(empty_parser):
    args = empty_parser.main_parser.parse_args(["list", "--no-dates"])
    assert args.no_dates is True


# ============================================================
# 3. HANDLER → MANAGER INTEGRATION (the glue code)
# ============================================================

def test_new_handler_calls_manager_with_correct_params(empty_parser):
    """_handle_new extracts args and calls manager.new correctly."""
    args = empty_parser.main_parser.parse_args([
        "new", "test task", "--status", "done"
    ])

    # We temporarily replace the manager's new method with a spy
    called_with = {}

    def mock_new(description, *, status, priority):
        called_with["description"] = description
        called_with["status"] = status
        called_with["priority"] = priority
        return True

    empty_parser.tasks_manager.new = mock_new

    result = args.func(args)

    assert result is True
    assert called_with["description"] == "test task"
    assert called_with["status"] == "done"
    assert called_with["priority"] == "low"  # default from parser config


def test_update_handler_calls_manager_with_correct_params(parser):
    """_handle_update extracts args and calls manager.update correctly."""
    args = parser.main_parser.parse_args([
        "update", "123", "--description", "new desc"
    ])

    called_with = {}

    def mock_update(id, *, new_descr, new_prior):
        called_with["id"] = id
        called_with["new_descr"] = new_descr
        called_with["new_prior"] = new_prior
        return True

    parser.tasks_manager.update = mock_update

    result = args.func(args)

    assert result is True
    assert called_with["id"] == "123"
    assert called_with["new_descr"] == "new desc"
    assert called_with["new_prior"] is None


def test_mark_handler_calls_manager_with_correct_params(parser):
    """_handle_mark extracts args and calls manager.mark correctly."""
    args = parser.main_parser.parse_args(["mark", "123", "done"])

    called_with = {}

    def mock_mark(id, new_status):
        called_with["id"] = id
        called_with["new_status"] = new_status
        return True

    parser.tasks_manager.mark = mock_mark

    result = args.func(args)

    assert result is True
    assert called_with["id"] == "123"
    assert called_with["new_status"] == "done"


def test_delete_handler_deduplicates_ids(parser):
    """_handle_delete deduplicates IDs before calling manager."""
    args = parser.main_parser.parse_args([
        "delete", "123", "456", "123", "-f"
    ])

    called_with = []

    def mock_delete(ids):
        called_with.append(ids)
        return ids

    parser.tasks_manager.delete = mock_delete

    result = args.func(args)

    assert result is True
    assert len(called_with) == 1
    assert called_with[0] == ["123", "456"]  # deduped


def test_delete_handler_validates_ids_before_prompting(parser):
    """All IDs must exist before any deletion occurs."""
    initial_len = len(parser.tasks_manager.tasks)
    args = parser.main_parser.parse_args(["delete", "123", "999", "-f"])

    with pytest.raises(KeyError) as exc_info:
        args.func(args)

    assert "999" in str(exc_info.value)
    assert len(parser.tasks_manager.tasks) == initial_len  # no deletion


# ============================================================
# 4. BUSSINES LOGIC FUNCTIONS
# ============================================================

def test_list_returns_sorted_ids(manager):
    """Test that list command returns tasks sorted by fields."""
    # Sort by status
    ids = manager.list(sort_by="status")
    assert ids == ["123", "111", "456"]  # not-done, in-progress, done
    ids = manager.list(sort_by="status", reverse=True)
    assert ids == ["123", "111", "456"][::-1] # reverse order
    
    # Sort by priority
    ids = manager.list(sort_by="priority")
    assert ids == ["123", "456", "111"]  # low, normal, urgent
    ids = manager.list(sort_by="priority", reverse=True)
    assert ids == ["123", "456", "111"][::-1]

    # Sort by created date
    ids = manager.list(sort_by="created")
    assert ids == ["456", "123", "111"]
    ids = manager.list(sort_by="created", reverse=True)
    assert ids == ["456", "123", "111"][::-1] 

    # Sort by updated date 
    ids = manager.list(sort_by="updated")
    assert ids == ["456", "111", "123"]
    ids = manager.list(sort_by="updated", reverse=True)
    assert ids == ["456", "111", "123"][::-1] 


# ============================================================
# 5. RETURN VALUES (mutation flags)
# ============================================================

def test_new_handler_returns_true(empty_parser):
    args = empty_parser.main_parser.parse_args(["new", "test"])
    result = args.func(args)
    assert result is True


def test_list_handler_returns_false(parser):
    args = parser.main_parser.parse_args(["list"])
    result = args.func(args)
    assert result is False


def test_update_handler_returns_true_when_changed(parser):
    args = parser.main_parser.parse_args([
        "update", "123", "--description", "new desc"
    ])
    result = args.func(args)
    assert result is True


def test_update_handler_raises_error_when_no_change(parser):
    args = parser.main_parser.parse_args([
        "update", "123", "--description", "read a book"
    ])
    with pytest.raises(ValueError, match="different"):
        args.func(args)


def test_delete_handler_returns_false_if_nothing_deleted(parser, monkeypatch):
    # monkeypatch simulates the user typing "n" when prompted
    monkeypatch.setattr("builtins.input", lambda: "n")
    args = parser.main_parser.parse_args(["delete", "123"])
    result = args.func(args)
    assert result is False
    assert "123" in parser.tasks_manager.tasks


def test_delete_handler_returns_true_when_forced(parser):
    args = parser.main_parser.parse_args(["delete", "123", "-f"])
    result = args.func(args)
    assert result is True
    assert "123" not in parser.tasks_manager.tasks


# ============================================================
# 6. USER INTERACTION (confirmation prompts)
# ============================================================

def test_delete_confirmation_deletes_on_yes(parser, monkeypatch):
    """When user types 'y', the task should be deleted."""
    # monkeypatch replaces input() so the test doesn't wait for keyboard input
    monkeypatch.setattr("builtins.input", lambda: "y")
    args = parser.main_parser.parse_args(["delete", "123"])
    result = args.func(args)
    assert result is True
    assert "123" not in parser.tasks_manager.tasks


def test_delete_confirmation_keeps_on_no(parser, monkeypatch):
    """When user types 'n', the task should be kept."""
    monkeypatch.setattr("builtins.input", lambda: "n")
    args = parser.main_parser.parse_args(["delete", "123"])
    result = args.func(args)
    assert result is False
    assert "123" in parser.tasks_manager.tasks


def test_delete_confirmation_asks_for_multiple_ids(parser, monkeypatch):
    """Multiple IDs prompt individually."""
    # We use an iterator to return different responses for each prompt
    inputs = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    args = parser.main_parser.parse_args(["delete", "123", "456"])
    result = args.func(args)

    assert result is True
    assert "123" not in parser.tasks_manager.tasks
    assert "456" not in parser.tasks_manager.tasks
    assert "111" in parser.tasks_manager.tasks


def test_delete_confirmation_one_cancelled_keeps_others(parser, monkeypatch):
    """Declining one ID doesn't prevent deletion of others."""
    inputs = iter(["y", "n"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    args = parser.main_parser.parse_args(["delete", "123", "456"])
    result = args.func(args)

    # Exactly one of 123 or 456 should be deleted
    assert ("123" in parser.tasks_manager.tasks) != ("456" in parser.tasks_manager.tasks)
    assert "111" in parser.tasks_manager.tasks


def test_delete_confirmation_aborts_on_keyboardinterrupt(parser, monkeypatch):
    """Ctrl+C during confirmation cancels entire operation."""
    def mock_confirm(*args, **kwargs):
        raise KeyboardInterrupt()

    # Patch the confirm_deletion name used inside cli module
    monkeypatch.setattr("easydone.cli.confirm_deletion", mock_confirm)

    args = parser.main_parser.parse_args(["delete", "123"])
    result = args.func(args)

    assert result is False
    assert "123" in parser.tasks_manager.tasks  # not deleted


# ============================================================
# 7. ERROR HANDLING
# ============================================================

def test_update_requires_at_least_one_change(parser, monkeypatch):
    """Update with no changes should error."""
    monkeypatch.setattr("sys.argv", ["easydone", "update", "123"])
    with pytest.raises(SystemExit):
        parser.start_parsing()


def test_missing_task_raises_keyerror(empty_parser):
    """Operations on missing tasks raise KeyError."""
    # Update
    args = empty_parser.main_parser.parse_args([
        "update", "999", "--description", "test"
    ])
    with pytest.raises(KeyError):
        args.func(args)

    # Mark
    args = empty_parser.main_parser.parse_args(["mark", "999", "done"])
    with pytest.raises(KeyError):
        args.func(args)

    # Delete
    args = empty_parser.main_parser.parse_args(["delete", "999", "-f"])
    with pytest.raises(KeyError):
        args.func(args)


def test_start_parsing_catches_exceptions_and_shows_message(empty_parser, capsys, monkeypatch):
    """start_parsing catches KeyError/ValueError and shows them."""
    # Simulate user running: easydone update 999 --description test
    monkeypatch.setattr("sys.argv", ["easydone", "update", "999", "--description", "test"])
    with pytest.raises(SystemExit):
        empty_parser.start_parsing()
    output = capsys.readouterr().err
    # main_parser.error prints to stderr
    assert "error" in output.lower() or "nonexistent" in output.lower()


# ============================================================
# 8. OUTPUT (list command)
# ============================================================

def test_list_shows_all_tasks(parser, capsys):
    args = parser.main_parser.parse_args(["list"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" in output
    assert "456" in output
    assert "111" in output


def test_list_filters_by_status(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--status", "done"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" not in output
    assert "456" in output
    assert "111" not in output


def test_list_filters_by_priority(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--priority", "low"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" in output
    assert "456" not in output
    assert "111" not in output


def test_list_filters_by_both(parser, capsys):
    args = parser.main_parser.parse_args([
        "list", "--status", "in-progress", "--priority", "urgent"
    ])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" not in output
    assert "456" not in output
    assert "111" in output

