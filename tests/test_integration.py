"""Integration tests for CLI parsing, handlers, and user-visible behavior.

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
└─────────────────────────────────────────────────────────────────────┘
These tests verify that:
- The CLI parser extracts arguments correctly
- Handlers call the manager methods with the right parameters
- User interaction (confirmation) works as expected
- Return values (mutation flags) are correct
- Errors are caught and displayed properly
- Commands render filtered task results as expected
"""

from datetime import date, timedelta

import pytest

from easydone import __version__
from easydone.cli import Parser


@pytest.fixture
def parser(manager):
    return Parser(manager)


@pytest.fixture
def empty_parser(empty_manager):
    return Parser(empty_manager)


# ----------------------------------------------------------------------------
# Version / Help
# ----------------------------------------------------------------------------


def test_version_output(empty_parser, capsys):
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(["-v"])
    assert __version__ in capsys.readouterr().out


def test_no_args_shows_help(empty_parser, capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["easydone"])
    assert empty_parser.start_parsing() is False
    assert "usage" in capsys.readouterr().out.lower()


# ----------------------------------------------------------------------------
# Parser Configuration
# ----------------------------------------------------------------------------


def test_new_parser_defaults(empty_parser):
    args = empty_parser.main_parser.parse_args(["new", "test"])
    assert args.status == "not-done" and args.priority == "low"


def test_new_parser_rejects_invalid(empty_parser):
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(["new", "test", "--status", "invalid"])
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(["new", "test", "--priority", "invalid"])


def test_update_parser_accepts_multiple_tag_options(parser):
    args = parser.main_parser.parse_args(
        [
            "update",
            "123",
            "--add-tag",
            "work",
            "urgent",
            "--remove-tag",
            "old",
        ]
    )

    assert args.add_tag == ["work", "urgent"]
    assert args.remove_tag == ["old"]


def test_bulk_command_parsers_accept_multiple_ids(parser):
    update_args = parser.main_parser.parse_args(["update", "123", "456", "--description", "shared"])
    mark_args = parser.main_parser.parse_args(["mark", "123", "456", "done"])
    list_args = parser.main_parser.parse_args(["list", "--tag", "work", "planning"])

    assert update_args.ids == ["123", "456"]
    assert mark_args.ids == ["123", "456"]
    assert list_args.tag == ["work", "planning"]


def test_list_parser_accepts_exclusive_filters(parser):
    args = parser.main_parser.parse_args(
        [
            "list",
            "--not-status",
            "done",
            "--not-priority",
            "low",
            "--not-tag",
            "personal",
            "blocked",
            "--not-overdue",
        ]
    )

    assert args.not_status == "done"
    assert args.not_priority == "low"
    assert args.not_tag == ["personal", "blocked"]
    assert args.not_overdue is True


# ----------------------------------------------------------------------------
# Handler Integration
# ----------------------------------------------------------------------------


def test_update_handler_requires_change(parser, monkeypatch):
    monkeypatch.setattr("sys.argv", ["easydone", "update", "123"])
    with pytest.raises(SystemExit):
        parser.start_parsing()


def test_delete_handler_deduplicates(parser):
    args = parser.main_parser.parse_args(["delete", "123", "456", "123", "-f"])
    called = []

    def mock_delete(ids):
        called.append(ids)
        return ids

    parser.tasks_manager.delete = mock_delete
    args.func(args)

    assert called == [["123", "456"]]  # deduped


def test_search_with_multiple_terms(parser):
    args = parser.main_parser.parse_args(["search", "go", "supermarket"])
    called = []

    def mock_search(query):
        called.append(query)
        return []

    parser.tasks_manager.search = mock_search
    args.func(args)

    assert called == [["go", "supermarket"]]


def test_search_with_no_dates(parser, capsys):
    """Search with --no-dates should omit dates from output."""
    args = parser.main_parser.parse_args(["search", "book", "--no-dates"])
    args.func(args)
    output = capsys.readouterr().out
    assert "Created at" not in output
    assert "Updated at" not in output


# ----------------------------------------------------------------------------
# Return Values (Mutation Flags)
# ----------------------------------------------------------------------------


def test_mutation_flags(empty_parser, parser, monkeypatch):
    # Read-only commands return False
    args = empty_parser.main_parser.parse_args(["list"])
    assert args.func(args) is False

    args = empty_parser.main_parser.parse_args(["search", "test"])
    assert args.func(args) is False

    # Mutating commands return True
    args = empty_parser.main_parser.parse_args(["new", "test"])
    assert args.func(args) is True

    args = parser.main_parser.parse_args(["update", "123", "--description", "new"])
    assert args.func(args) is True

    # Delete with no confirmation returns False
    monkeypatch.setattr("builtins.input", lambda: "n")
    args = parser.main_parser.parse_args(["delete", "123"])
    assert args.func(args) is False

    # Forced delete returns True
    args = parser.main_parser.parse_args(["delete", "123", "-f"])
    assert args.func(args) is True


# ----------------------------------------------------------------------------
# User Interaction (Confirmation)
# ----------------------------------------------------------------------------


def test_confirmation_flow(parser, monkeypatch):
    # "y" → delete
    monkeypatch.setattr("builtins.input", lambda: "y")
    args = parser.main_parser.parse_args(["delete", "123"])
    assert args.func(args) is True
    assert "123" not in parser.tasks_manager.tasks

    # "n" → keep
    monkeypatch.setattr("builtins.input", lambda: "n")
    args = parser.main_parser.parse_args(["delete", "456"])
    assert args.func(args) is False
    assert "456" in parser.tasks_manager.tasks


def test_keyboardinterrupt_cancels_deletion(parser, monkeypatch):
    def mock_confirm(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("easydone.cli.confirm_deletion", mock_confirm)
    args = parser.main_parser.parse_args(["delete", "123"])
    assert args.func(args) is False
    assert "123" in parser.tasks_manager.tasks


# ----------------------------------------------------------------------------
# Error Handling
# ----------------------------------------------------------------------------


def test_missing_task_raises_keyerror(empty_parser):
    args = empty_parser.main_parser.parse_args(["update", "999", "--description", "x"])
    with pytest.raises(KeyError):
        args.func(args)

    args = empty_parser.main_parser.parse_args(["mark", "999", "done"])
    with pytest.raises(KeyError):
        args.func(args)

    args = empty_parser.main_parser.parse_args(["delete", "999", "-f"])
    with pytest.raises(KeyError):
        args.func(args)


def test_start_parsing_catches_errors(empty_parser, capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["easydone", "update", "999", "--description", "x"])
    with pytest.raises(SystemExit):
        empty_parser.start_parsing()
    assert "error" in capsys.readouterr().err.lower()


# ----------------------------------------------------------------------------
# Command Output
# ----------------------------------------------------------------------------


def test_list_output(parser, capsys):
    args = parser.main_parser.parse_args(["list"])
    args.func(args)
    output = capsys.readouterr().out
    for id in ["123", "456", "111"]:
        assert id in output


def test_list_filters(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--status", "done"])
    args.func(args)
    output = capsys.readouterr().out
    assert "456" in output and "123" not in output and "111" not in output

    args = parser.main_parser.parse_args(["list", "--priority", "low"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" in output and "456" not in output and "111" not in output


def test_list_command_applies_exclusive_filters(parser, capsys):
    parser.tasks_manager.tasks["123"]["tags"] = ["work"]
    parser.tasks_manager.tasks["456"]["tags"] = ["personal"]
    parser.tasks_manager.tasks["111"]["tags"] = ["work", "personal"]

    args = parser.main_parser.parse_args(
        ["list", "--not-status", "done", "--not-tag", "personal"]
    )
    args.func(args)
    output = capsys.readouterr().out

    assert "123" in output
    assert "456" not in output
    assert "111" not in output

    args = parser.main_parser.parse_args(["list", "--not-priority", "low"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" not in output
    assert "456" in output
    assert "111" in output

    parser.tasks_manager.tasks["123"]["due"] = (date.today() - timedelta(days=1)).isoformat()
    parser.tasks_manager.tasks["456"]["due"] = (date.today() - timedelta(days=1)).isoformat()
    parser.tasks_manager.tasks["111"]["due"] = (date.today() + timedelta(days=1)).isoformat()
    args = parser.main_parser.parse_args(["list", "--not-overdue"])
    args.func(args)
    output = capsys.readouterr().out
    assert "123" not in output
    assert "456" not in output
    assert "111" in output


def test_list_no_dates(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--no-dates"])
    args.func(args)
    output = capsys.readouterr().out
    assert "Created at" not in output
    assert "Updated at" not in output


def test_list_command_supports_sorting_and_compact_output(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--sort", "priority", "--reverse", "--no-dates"])
    args.func(args)
    output = capsys.readouterr().out

    assert output.index("111") < output.index("456") < output.index("123")
    assert "Created at" not in output
    assert "Updated at" not in output
    assert "Due:" not in output


def test_list_command_reports_no_matching_filters(parser, capsys):
    args = parser.main_parser.parse_args(["list", "--status", "done", "--priority", "low"])
    args.func(args)

    assert "No tasks match the selected filters." in capsys.readouterr().out


def test_list_command_reports_empty_task_collection(empty_parser, capsys):
    args = empty_parser.main_parser.parse_args(["list", "--not-status", "done"])
    args.func(args)

    assert "No tasks exist." in capsys.readouterr().out


def test_stats(parser, capsys):
    args = parser.main_parser.parse_args(["stats"])
    args.func(args)
    output = capsys.readouterr().out
    
    terms = ["EasyDone stats", "in total", "low", "normal", "high", "urgent", "not-done", "in-progress", "priority", "status", "overdue", "near overdue"]
    assert all([term in output for term in terms])
