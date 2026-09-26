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
└─────────────────────────────────────────────────────────────────────┘
These tests verify that:
- The CLI parser extracts arguments correctly
- Handlers call the manager methods with the right parameters
- User interaction (confirmation) works as expected
- Return values (mutation flags) are correct
- Errors are caught and displayed properly
"""

from datetime import date, datetime, timedelta

import pytest

from easydone import __version__
from easydone.cli import Parser
from easydone.logic import TasksManager, Stats, normalize_due_date

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def manager():
    """TasksManager with 3 tasks at different dates for sorting tests."""
    date = datetime.now()
    return TasksManager(
        {
            "123": {
                "description": "read a book",
                "status": "not-done",
                "priority": "low",
                "created-at": str(date + timedelta(days=3)).split(" ")[0],
                "updated-at": str(date + timedelta(days=9)).split(" ")[0],
            },
            "456": {
                "description": "write code",
                "status": "done",
                "priority": "normal",
                "created-at": str(date).split(" ")[0],
                "updated-at": str(date + timedelta(days=4)).split(" ")[0],
            },
            "111": {
                "description": "go supermarket",
                "status": "in-progress",
                "priority": "urgent",
                "created-at": str(date + timedelta(days=5)).split(" ")[0],
                "updated-at": str(date + timedelta(days=7)).split(" ")[0],
            },
        }
    )


@pytest.fixture
def empty_manager():
    return TasksManager({})


@pytest.fixture
def parser(manager):
    return Parser(manager)


@pytest.fixture
def empty_parser(empty_manager):
    return Parser(empty_manager)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


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


def test_new_tasks_start_with_empty_tags(empty_manager):
    empty_manager.new("test")

    task = next(iter(empty_manager.tasks.values()))
    assert task["tags"] == []


def test_new_parser_rejects_invalid(empty_parser):
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(["new", "test", "--status", "invalid"])
    with pytest.raises(SystemExit):
        empty_parser.main_parser.parse_args(["new", "test", "--priority", "invalid"])


def test_new_rejects_impossible_due_date(empty_manager):
    with pytest.raises(ValueError, match="Invalid due date"):
        empty_manager.new("test", due_date="2026-02-30")


def test_new_rejects_clear_due_date(empty_manager):
    with pytest.raises(ValueError, match="Clear can only be used"):
        empty_manager.new("test", due_date="Clear")


def test_update_rejects_unchanged_due_date(manager):
    manager.tasks["123"]["due"] = "2026-09-10"

    with pytest.raises(ValueError, match="different from the current one"):
        manager.update("123", new_due="2026-09-10")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Clear", None),
        ("Tomorrow", "2026-09-02"),
        ("+3", "2026-09-04"),
        ("-2", "2026-08-30"),
    ],
)
def test_normalize_due_date_keywords(value, expected):
    assert normalize_due_date(value, today=date(2026, 9, 1)) == expected


def test_update_can_clear_due_date(manager):
    manager.tasks["123"]["due"] = "2026-09-10"

    assert manager.update("123", new_due="Clear") is True
    assert manager.tasks["123"]["due"] is None


def test_update_rejects_clear_when_task_has_no_due_date(manager):
    manager.tasks["123"]["due"] = None

    with pytest.raises(ValueError, match="different from the current one"):
        manager.update("123", new_due="Clear")


def test_update_without_due_date_does_not_change_due_date(manager):
    manager.tasks["123"]["due"] = "2026-09-10"

    assert manager.update("123", new_descr="new description") is True
    assert manager.tasks["123"]["due"] == "2026-09-10"


def test_update_adds_and_removes_tags(manager):
    manager.tasks["123"]["tags"] = ["work"]

    assert (
        manager.update(
            "123",
            add_tags=["urgent", "work"],
            remove_tags=["work"],
        )
        is True
    )
    assert manager.tasks["123"]["tags"] == ["urgent"]


def test_update_tags_is_backward_compatible_for_legacy_tasks(manager):
    manager.tasks["123"].pop("tags", None)

    assert manager.update("123", add_tags=["work"]) is True
    assert manager.tasks["123"]["tags"] == ["work"]


def test_legacy_tasks_receive_empty_tags(manager):
    manager.tasks["123"].pop("tags", None)

    TasksManager(manager.tasks)

    assert manager.tasks["123"]["tags"] == []


def test_existing_tags_are_normalized_when_manager_is_created(manager):
    manager.tasks["123"]["tags"] = [" work ", "work", "urgent"]

    TasksManager(manager.tasks)

    assert manager.tasks["123"]["tags"] == ["work", "urgent"]


def test_update_ignores_redundant_tag_changes(manager):
    manager.tasks["123"]["tags"] = ["work"]

    assert manager.update("123", add_tags=["work"]) is False
    assert manager.update("123", remove_tags=["missing"]) is False


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


def test_list_filters_by_all_tags(manager):
    manager.tasks["123"]["tags"] = ["work", "planning"]
    manager.tasks["456"]["tags"] = ["work"]
    manager.tasks["111"]["tags"] = ["personal"]

    assert manager.list(filt_tags=["work"]) == ["123", "456"]
    assert manager.list(filt_tags=["work", "planning"]) == ["123"]


def test_list_excludes_tasks_by_status_priority_and_tags(manager):
    manager.tasks["123"]["tags"] = ["work", "planning"]
    manager.tasks["456"]["tags"] = ["work"]
    manager.tasks["111"]["tags"] = ["personal", "planning"]

    assert manager.list(exclude_status="done") == ["123", "111"]
    assert manager.list(exclude_priority="low") == ["456", "111"]
    assert manager.list(exclude_tags=["work", "planning"]) == ["456", "111"]


def test_list_combines_inclusion_and_exclusion_filters(manager):
    manager.tasks["123"]["tags"] = ["work"]
    manager.tasks["456"]["tags"] = ["work", "planning"]
    manager.tasks["111"]["tags"] = ["personal"]

    assert manager.list(
        filt_tags=["work"],
        exclude_status="done",
        exclude_priority="low",
    ) == []
    assert manager.list(filt_tags=["work"], exclude_status="in-progress") == ["123", "456"]


def test_list_filters_overdue_and_excludes_in_progress(manager):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    manager.tasks["123"]["due"] = yesterday
    manager.tasks["456"]["due"] = yesterday
    manager.tasks["111"]["due"] = tomorrow

    assert manager.list(filt_overdue=True) == ["123", "456"]
    assert manager.list(filt_overdue=True, exclude_status="done") == ["123"]
    assert manager.list(exclude_overdue=True) == ["111"]


def test_mark_many_validates_all_ids_before_mutating(manager):
    with pytest.raises(KeyError):
        manager.mark_many(["123", "missing"], "done")

    assert manager.tasks["123"]["status"] == "not-done"


def test_update_many_rolls_back_if_one_task_fails(manager):
    with pytest.raises(ValueError, match="different from the current one"):
        manager.update_many(
            ["123", "456"],
            new_prior="normal",
        )

    assert manager.tasks["123"]["priority"] == "low"
    assert manager.tasks["456"]["priority"] == "normal"


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


def test_global_no_dates_flag(empty_parser):
    args = empty_parser.main_parser.parse_args(["--no-dates", "list"])
    assert args.no_dates is True

def test_stats_returns_correct_values(manager):
    tasks = manager.tasks
    tasks['123']['due'] = str(datetime.now() - timedelta(days=1)).split(" ")[0]
    tasks['456']['due'] = str(datetime.now() + timedelta(days=3)).split(" ")[0]
    stats = manager.stats()
    
    assert isinstance(stats, Stats)
    assert stats.total_tasks == 3
    assert stats.total_by_priority['low'] == 1
    assert stats.total_by_priority['normal'] == 1
    assert stats.total_by_priority['high'] == 0
    assert stats.total_by_priority['urgent'] == 1
    assert stats.total_by_status['done'] == 1
    assert stats.total_by_status['not-done'] == 1
    assert stats.total_by_status['in-progress'] == 1
    assert stats.total_overdue == 1
    assert stats.total_near_overdue == 1

# ----------------------------------------------------------------------------
# 3. Handlers → Manager Integration
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
    args = parser.main_parser.parse_args(["--no-dates", "search", "book"])
    args.func(args)
    output = capsys.readouterr().out
    assert "Created at" not in output
    assert "Updated at" not in output


# ----------------------------------------------------------------------------
# Sorting (Logic)
# ----------------------------------------------------------------------------


def test_list_sorting_logic(manager):
    """Sorting at the manager level works correctly."""
    # Status: not-done (123), in-progress (111), done (456)
    assert manager.list(sort_by="status") == ["123", "111", "456"]
    assert manager.list(sort_by="status", reverse=True) == ["456", "111", "123"]

    # Priority: low (123), normal (456), urgent (111)
    assert manager.list(sort_by="priority") == ["123", "456", "111"]
    assert manager.list(sort_by="priority", reverse=True) == ["111", "456", "123"]

    # Created: oldest (456), then (123), then (111)
    assert manager.list(sort_by="created") == ["456", "123", "111"]
    assert manager.list(sort_by="created", reverse=True) == ["111", "123", "456"]

    # Updated: (456), then (111), then (123)
    assert manager.list(sort_by="updated") == ["456", "111", "123"]
    assert manager.list(sort_by="updated", reverse=True) == ["123", "111", "456"]


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
# 10. Output (List, Stats)
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
    args = parser.main_parser.parse_args(["--no-dates", "list"])
    args.func(args)
    output = capsys.readouterr().out
    assert "Created at" not in output
    assert "Updated at" not in output


def test_list_command_supports_sorting_and_compact_output(parser, capsys):
    args = parser.main_parser.parse_args(["--no-dates", "list", "--sort", "priority", "--reverse"])
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
