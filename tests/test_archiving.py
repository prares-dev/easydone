"""Tests for task archiving across logic, CLI, and persisted application behavior."""

from datetime import date

import pytest

from easydone.__main__ import main
from easydone.cli import Parser
from easydone.logic import TasksManager
from easydone.storage import JSONHandler


@pytest.fixture
def manager() -> TasksManager:
    """Manager with two active tasks and one completed task."""
    return TasksManager(
        {
            "123": {
                "description": "write a report",
                "status": "not-done",
                "priority": "low",
                "due": None,
            },
            "456": {
                "description": "read a book",
                "status": "done",
                "priority": "normal",
                "due": None,
            },
            "789": {
                "description": "review code",
                "status": "in-progress",
                "priority": "urgent",
                "due": None,
            },
        }
    )


@pytest.fixture
def parser(manager: TasksManager) -> Parser:
    return Parser(manager)


def test_archive_and_restore_many_validate_all_ids_before_mutating(manager):
    with pytest.raises(KeyError, match="missing"):
        manager.archive_many(["123", "missing"])
    assert "archived-at" not in manager.tasks["123"]

    assert manager.archive_many(["123", "123", "456"]) is True
    assert manager.tasks["123"]["archived-at"] == date.today().isoformat()
    assert manager.tasks["456"]["archived-at"] == date.today().isoformat()

    with pytest.raises(KeyError, match="missing"):
        manager.restore_many(["123", "missing"])
    assert manager.tasks["123"]["archived-at"] == date.today().isoformat()

    assert manager.restore_many(["123", "123", "456"]) is True
    assert manager.tasks["123"]["archived-at"] is None
    assert manager.tasks["456"]["archived-at"] is None
    assert manager.archive_many([]) is False
    assert manager.restore_many([]) is False


def test_list_filters_archived_tasks(manager):
    manager.archive_many(["456"])

    assert manager.list() == ["123", "789"]
    assert manager.list(archived_only=True) == ["456"]
    assert manager.list(include_archived=True) == ["123", "456", "789"]


def test_search_excludes_archived_tasks(manager):
    manager.archive_many(["123"])

    assert manager.search(["report"]) == []
    assert manager.search(["book"]) == ["456"]


def test_stats_counts_archived_tasks_separately(manager):
    manager.archive_many(["456"])

    stats = manager.stats()

    assert stats.total_tasks == 2
    assert stats.total_archived == 1
    assert stats.total_by_priority == {"low": 1, "normal": 0, "high": 0, "urgent": 1}
    assert stats.total_by_status == {"not-done": 1, "in-progress": 1, "done": 0}


def test_stats_handles_all_tasks_archived(manager):
    manager.archive_many(list(manager.tasks))

    stats = manager.stats()

    assert stats.total_tasks == 0
    assert stats.total_archived == 3
    assert sum(stats.total_by_priority.values()) == 0
    assert sum(stats.total_by_status.values()) == 0


def test_archive_list_options_are_mutually_exclusive(parser):
    with pytest.raises(SystemExit):
        parser.main_parser.parse_args(["list", "--archived", "--with-archived"])


def test_archive_and_restore_commands_are_mutations(parser):
    archive_args = parser.main_parser.parse_args(["archive", "123", "456", "123"])
    assert archive_args.func(archive_args) is True
    assert parser.tasks_manager.tasks["123"]["archived-at"]
    assert parser.tasks_manager.tasks["456"]["archived-at"]

    restore_args = parser.main_parser.parse_args(["restore", "123", "456"])
    assert restore_args.func(restore_args) is True
    assert parser.tasks_manager.tasks["123"]["archived-at"] is None
    assert parser.tasks_manager.tasks["456"]["archived-at"] is None


def test_archive_commands_persist_through_application_entry_point(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "tasks.json"
    monkeypatch.setenv("EASYDONE_DATA_FILE", str(data_file))
    JSONHandler(str(data_file)).save(
        {
            "123": {
                "description": "finish project",
                "status": "done",
                "priority": "normal",
                "due": None,
                "tags": [],
                "created-at": date.today().isoformat(),
                "updated-at": None,
            }
        }
    )

    monkeypatch.setattr("sys.argv", ["easydone", "archive", "123"])
    main()
    capsys.readouterr()
    assert JSONHandler(str(data_file)).load().tasks["123"]["archived-at"]

    monkeypatch.setattr("sys.argv", ["easydone", "restore", "123"])
    main()
    capsys.readouterr()
    assert JSONHandler(str(data_file)).load().tasks["123"]["archived-at"] is None


def test_list_command_shows_archived_modes(parser, capsys):
    parser.tasks_manager.archive_many(["456"])

    args = parser.main_parser.parse_args(["list", "--archived"])
    args.func(args)
    output = capsys.readouterr().out
    assert "456" in output
    assert "123" not in output
    assert "789" not in output

    args = parser.main_parser.parse_args(["list", "--with-archived"])
    args.func(args)
    output = capsys.readouterr().out
    for task_id in ("123", "456", "789"):
        assert task_id in output
