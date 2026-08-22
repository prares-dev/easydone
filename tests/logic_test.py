"""Tests for the CLI application and its task-management commands.

Pytest injects fixtures into a test function when their names appear in the
function parameters. The local ``new_instance`` and ``from_json_instance``
fixtures provide fresh ``CLIApp`` objects for each test. Built-in fixtures
used here include:

* ``monkeypatch`` temporarily replaces ``input`` so confirmation prompts can
    be tested without waiting for terminal input. The replacement is restored
    automatically after the test.
* ``capsys`` captures text written to stdout, allowing list-command output to
    be asserted without displaying it during the test run.

Keeping setup in fixtures makes each test focus on the command behavior it is
checking.
"""

import pytest
from datetime import datetime

from easydone.cli import CLIApp
from easydone.logic import TasksManager

# ===========
# FIXTURES
# ===========

@pytest.fixture
def new_instance() -> CLIApp:
    """Return a CLI application with no existing tasks."""
    return CLIApp({})

@pytest.fixture
def from_json_instance() -> CLIApp:
    """Return a CLI application populated with representative task states."""
    return CLIApp({
        "123": {
            "description": "read a book",
            "status": "not-done",
            "priority": "low",
            "created-at": "2026-08-22",
            "updated-at": None
        },
        "456": {
            "description": "write code",
            "status": "done",
            "priority": "normal",
            "created-at": "2026-08-22",
            "updated-at": None
        },
        "111": {
            "description": "go supermarket",
            "status": "in-progress",
            "priority": "urgent",
            "created-at": "2026-08-22",
            "updated-at": None
        }
    })

# ===========
# TESTS
# ===========

def test_empty_tasks_when_init(new_instance):
    """A new application should start with an empty task collection."""
    tasks = new_instance.tasks_manager.tasks
    assert len(tasks) == 0

def test_adding_a_new_task(new_instance):
    """The new command should create a task with its supplied options."""
    tasks = new_instance.tasks_manager.tasks

    args = new_instance.main_parser.parse_args([
        "new",
        "read a book",
        "--status",
        "done",
        "--priority",
        "high",
    ])
    args.func(args)

    assert len(tasks) == 1
    task_id = next(iter(tasks))
    assert tasks[task_id] == {
        "description": "read a book",
        "status": "done",
        "priority": "high",
        "created-at": str(datetime.now()).split(" ")[0],
        "updated-at": None
    }

def test_adding_new_task_on_top_of_existent(from_json_instance):
    """Adding a task should preserve all tasks that already exist."""
    tasks = from_json_instance.tasks_manager.tasks
    original_keys = list(tasks.keys())
    original_len = len(tasks)

    args = from_json_instance.main_parser.parse_args([
        "new",
        "read another book",
        "--status",
        "in-progress",
        "--priority",
        "urgent",
    ])
    args.func(args)

    assert len(tasks) == original_len + 1
    assert any(task["description"] == "read another book" for task in tasks.values())
    for key in original_keys:
        assert key in tasks

def test_task_id_has_ID_SIZE_digits(new_instance):
    """Generated task IDs should always contain three digits."""
    task_id = new_instance.tasks_manager.task_id()

    assert len(task_id) == new_instance.tasks_manager.ID_SIZE
    assert task_id.isdigit()

def test_task_id_retries_when_generated_id_already_exists(monkeypatch):
    """ID generation should retry instead of overwriting an existing task."""
    manager = TasksManager({"123": {}})
    generated_digits = iter([1, 2, 3, 4, 5, 6])
    monkeypatch.setattr("easydone.logic.randint", lambda _start, _end: next(generated_digits))

    assert manager.task_id() == "456"

def test_update_existing_task(from_json_instance):
    """The update command should change only the requested task fields."""
    tasks = from_json_instance.tasks_manager.tasks
    task_id = "123"

    args = from_json_instance.main_parser.parse_args([
        "update",
        task_id,
        "--description",
        "read a novel",
        "--priority",
        "high",
    ])

    args.func(args)

    assert tasks[task_id]["description"] == "read a novel"
    assert tasks[task_id]["priority"] == "high"
    assert tasks[task_id]["status"] == "not-done"
    
    date = str(datetime.now()).split(" ")[0]
    assert tasks[task_id]["created-at"] == date
    assert tasks[task_id]["updated-at"] == date

def test_mark_task_status(from_json_instance):
    """The mark command should replace an existing task's status."""
    tasks = from_json_instance.tasks_manager.tasks

    args = from_json_instance.main_parser.parse_args([
        "mark",
        "456",
        "done",
    ])

    args.func(args)

    assert tasks["456"]["status"] == "done"

def test_delete_existing_task(from_json_instance):
    """The forced delete option should remove a task without prompting."""
    tasks = from_json_instance.tasks_manager.tasks
    assert "123" in tasks
    
    args = from_json_instance.main_parser.parse_args(
        ["delete", 
        "123",
        "-f"])
    
    args.func(args)
    assert "123" not in tasks

def test_delete_task_after_confirmation(from_json_instance, monkeypatch):
    """A yes response to the delete prompt should remove the task."""
    monkeypatch.setattr("builtins.input", lambda _: "y")

    args = from_json_instance.main_parser.parse_args([
        "delete",
        "123",
    ])

    args.func(args)

    assert "123" not in from_json_instance.tasks_manager.tasks

def test_keep_task_when_deletion_is_rejected(from_json_instance, monkeypatch):
    """A no response to the delete prompt should keep the task."""
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = from_json_instance.main_parser.parse_args(["delete", "123"])
    args.func(args)

    assert "123" in from_json_instance.tasks_manager.tasks

def test_update_delete_and_mark_raise_key_error_for_missing_tasks(new_instance):
    """Update, mark, and delete should reject unknown task IDs."""
    update_args = new_instance.main_parser.parse_args([
        "update",
        "missing-id",
        "--description",
        "new title",
    ])
    mark_args = new_instance.main_parser.parse_args([
        "mark",
        "missing-id",
        "done",
    ])
    delete_args = new_instance.main_parser.parse_args([
        "delete",
        "missing-id",
        "-f",
    ])

    with pytest.raises(KeyError):
        update_args.func(update_args)

    with pytest.raises(KeyError):
        mark_args.func(mark_args)
    
    with pytest.raises(KeyError):
        delete_args.func(delete_args)

def test_list_without_filters(from_json_instance, capsys):
    """The list command without filters should print every task."""
    args = from_json_instance.main_parser.parse_args(["list"])

    args.func(args)

    output = capsys.readouterr().out
    assert 'ID: 123 "read a book" [low] [not-done]' in output
    assert 'ID: 456 "write code" [normal] [done]' in output
    assert 'ID: 111 "go supermarket" [urgent] [in-progress]' in output

def test_list_filters_by_status(from_json_instance, capsys):
    """The status option should print only tasks with that status."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--status",
        "done",
    ])

    args.func(args)

    output = capsys.readouterr().out
    assert 'ID: 123 "read a book" [low] [not-done]' not in output
    assert 'ID: 456 "write code" [normal] [done]' in output
    assert 'ID: 111 "go supermarket" [urgent] [in-progress]' not in output

def test_list_filters_by_priority(from_json_instance, capsys):
    """The priority option should print only tasks with that priority."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--priority",
        "low",
    ])

    args.func(args)

    output = capsys.readouterr().out
    assert 'ID: 123 "read a book" [low] [not-done]' in output
    assert 'ID: 456 "write code" [normal] [done]' not in output
    assert 'ID: 111 "go supermarket" [urgent] [in-progress]' not in output

def test_list_filters_by_status_and_priority(from_json_instance, capsys):
    """Status and priority options should be applied together."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--status",
        "in-progress",
        "--priority",
        "urgent",
    ])

    args.func(args)

    output = capsys.readouterr().out
    assert 'ID: 123 "read a book" [low] [not-done]' not in output
    assert 'ID: 456 "write code" [normal] [done]' not in output
    assert 'ID: 111 "go supermarket" [urgent] [in-progress]' in output