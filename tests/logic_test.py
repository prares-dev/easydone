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

from easydone import __version__
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

    date = str(datetime.now()).split(" ")[0]

    return CLIApp({
        "123": {
            "description": "read a book",
            "status": "not-done",
            "priority": "low",
            "created-at": date,
            "updated-at": None
        },
        "456": {
            "description": "write code",
            "status": "done",
            "priority": "normal",
            "created-at": date,
            "updated-at": None
        },
        "111": {
            "description": "go supermarket",
            "status": "in-progress",
            "priority": "urgent",
            "created-at": date,
            "updated-at": None
        }
    })

# ===========
# TESTS
# ===========

def test_get_current_verison(new_instance, capsys):
    """Running -v or --version should output the correct version of the program."""
    with pytest.raises(SystemExit):
        new_instance.main_parser.parse_args(['-v'])
        output = capsys.readouterr().out
        assert __version__ in output
    
    with pytest.raises(SystemExit):
        new_instance.main_parser.parse_args(['--version'])
        output = capsys.readouterr().out
        assert __version__ in output

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
    initial_date = tasks[task_id]["created-at"]

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
    assert tasks[task_id]["created-at"] == initial_date
    assert tasks[task_id]["updated-at"] == str(datetime.now()).split(" ")[0]


def test_update_existing_task_with_single_field(from_json_instance):
    """A single update option should preserve the remaining task data."""
    tasks = from_json_instance.tasks_manager.tasks
    task_id = "123"
    initial_date = tasks[task_id]["created-at"]

    args = from_json_instance.main_parser.parse_args([
        "update",
        task_id,
        "--priority",
        "high",
    ])

    args.func(args)

    assert tasks[task_id]["description"] == "read a book"
    assert tasks[task_id]["priority"] == "high"
    assert tasks[task_id]["status"] == "not-done"
    assert tasks[task_id]["created-at"] == initial_date
    assert tasks[task_id]["updated-at"] == str(datetime.now()).split(" ")[0]


def test_update_requires_at_least_one_change(from_json_instance, monkeypatch):
    """The update command should reject calls with no actual field changes."""
    monkeypatch.setattr("sys.argv", ["easydone", "update", "123"])

    with pytest.raises(SystemExit):
        from_json_instance.start_parsing()


def test_update_rejects_same_description_and_priority(from_json_instance):
    """The update command should reject values identical to the stored task."""
    same_description = from_json_instance.main_parser.parse_args([
        "update",
        "123",
        "--description",
        "read a book",
    ])
    same_priority = from_json_instance.main_parser.parse_args([
        "update",
        "123",
        "--priority",
        "low",
    ])

    with pytest.raises(ValueError, match="different"):
        from_json_instance.tasks_manager.update(same_description)

    with pytest.raises(ValueError, match="different"):
        from_json_instance.tasks_manager.update(same_priority)

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

def test_list_without_filters(from_json_instance):
    """The list command without filters should return every task ID."""
    args = from_json_instance.main_parser.parse_args(["list"])

    result = args.func(args)

    assert '123' in result
    assert '456' in result
    assert '111' in result

def test_list_filters_by_status(from_json_instance):
    """The status option should return only tasks with that status."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--status",
        "done",
    ])

    result = args.func(args)

    assert '123' not in result
    assert '456' in result
    assert '111' not in result

def test_list_filters_by_priority(from_json_instance):
    """The priority option should return only tasks with that priority."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--priority",
        "low",
    ])

    result = args.func(args)

    assert '123' in result
    assert '456' not in result
    assert '111' not in result

def test_list_filters_by_status_and_priority(from_json_instance):
    """Status and priority options should be applied together."""
    args = from_json_instance.main_parser.parse_args([
        "list",
        "--status",
        "in-progress",
        "--priority",
        "urgent",
    ])

    result = args.func(args)

    assert '123' not in result
    assert '456' not in result
    assert '111' in result