"""

┌─────────────────────────────────────────────────────────────────────┐
│ FIXTURES: The "tools" pytest gives us                               │
├─────────────────────────────────────────────────────────────────────┤ 
│                                                                     │
│ tmp_path    - Creates a temporary directory that's cleaned up.      │
│               Use it for file operations without affecting          │
│               your real data.                                       │
│               Example: json_file = tmp_path / "tasks.json"          │
└─────────────────────────────────────────────────────────────────────┘

"""

import json
import shutil

import pytest

from easydone import __version__
from easydone.storage import JSONHandler, LoadingResult, LoadStatus, CURRENT_SCHEMA_VERSION


@pytest.fixture
def tasks() -> dict[str, dict]:
    return {
        "064": {
            "description": "do homework",
            "status": "not-done",
            "priority": "low",
            "created-at": "2026-08-22",
            "updated-at": None,
        },
        "722": {
            "description": "do house shores",
            "status": "not-done",
            "priority": "low",
            "created-at": "2026-08-22",
            "updated-at": "2026-08-22",
        },
    }


def _write_payload(json_file, **overrides):
    """Write a well-formed payload, letting callers override individual fields
    (schema_version, app_version, tasks, saved_at) to trigger specific paths."""
    payload = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "app_version": __version__,
        "saved_at": "2026-08-24",
        "tasks": {},
    }
    payload.update(overrides)
    json_file.write_text(json.dumps(payload), encoding="utf-8")


# ===========
# Happy path
# ===========

def test_load_returns_existing_tasks_with_no_warnings(tmp_path, tasks):
    """A well-formed, up-to-date file should load cleanly: no corruption, no warning."""
    json_file = tmp_path / "tasks.json"
    _write_payload(json_file, tasks=tasks)

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert isinstance(result, LoadingResult)
    assert result.tasks == tasks
    assert result.status is LoadStatus.OK


def test_save_writes_tasks_to_json_file(tmp_path, tasks):
    """save() is unaffected by the LoadingResult refactor: it still writes a plain payload."""
    json_file = tmp_path / "tasks.json"

    handler = JSONHandler(str(json_file))
    handler.save(tasks)

    saved_data = json.loads(json_file.read_text(encoding="utf-8"))

    assert saved_data["schema_version"] == CURRENT_SCHEMA_VERSION
    assert saved_data["app_version"] == handler.app_version
    assert saved_data["tasks"] == tasks


def test_save_then_load_round_trips_without_warnings(tmp_path, tasks):
    """A file this app just wrote should always load back cleanly."""
    json_file = tmp_path / "tasks.json"
    handler = JSONHandler(str(json_file))

    handler.save(tasks)
    result = handler.load()

    assert result.tasks == tasks
    assert result.status is LoadStatus.OK


# ==========================
# Missing file (not corrupted)
# ==========================

def test_load_returns_empty_result_when_file_is_missing(tmp_path):
    """A missing file is a normal first-run case, not corruption."""
    missing_file = tmp_path / "missing_tasks.json"
    handler = JSONHandler(str(missing_file))

    result = handler.load()

    assert result.tasks == {}
    assert result.status is LoadStatus.MISSING
    assert not missing_file.exists()


# ==========================
# Corruption: must NOT silently look like "no tasks yet"
# ==========================

def test_load_flags_malformed_json_as_corrupted(tmp_path):
    """Invalid JSON must be reported as corrupted, not treated as an empty task list."""
    json_file = tmp_path / "tasks.json"
    json_file.write_text("{not valid json", encoding="utf-8")

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.CORRUPTED
    assert result.tasks == {}


def test_load_flags_non_dict_payload_as_corrupted(tmp_path):
    """A JSON file that isn't an object at the top level (e.g. a bare list) is corrupted."""
    json_file = tmp_path / "tasks.json"
    json_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.CORRUPTED
    assert result.tasks == {}


def test_load_flags_wrapperless_dict_as_corrupted(tmp_path, tasks):
    """
    Pre-schema files (a bare {id: task} dict with no metadata wrapper) are no
    longer auto-detected and loaded. There has been no release that ever wrote
    this shape as its saved format, so this isn't a real migration path yet -
    treating it as corrupted (rather than guessing at a migration) is the
    conservative choice. Revisit this once a shipped schema_version needs a
    real upgrade path from an earlier one.
    """
    json_file = tmp_path / "tasks.json"
    json_file.write_text(json.dumps(tasks), encoding="utf-8")

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.CORRUPTED
    assert result.tasks == {}


def test_load_flags_non_dict_tasks_field_as_corrupted(tmp_path):
    """If 'tasks' exists but isn't itself a dict, the payload is unusable."""
    json_file = tmp_path / "tasks.json"
    _write_payload(json_file, tasks=["not", "a", "dict"])

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.CORRUPTED
    assert result.tasks == {}


# ==========================
# Warnings: tasks ARE usable, but flag for review
# ==========================

def test_load_warns_on_newer_schema_version(tmp_path, tasks):
    """A schema from a future version of the app should load but warn, not discard data."""
    json_file = tmp_path / "tasks.json"
    _write_payload(json_file, schema_version=CURRENT_SCHEMA_VERSION + 1, tasks=tasks)

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.found_schema_version == CURRENT_SCHEMA_VERSION + 1
    assert result.schema_mismatch is True
    assert result.status is LoadStatus.OK
    assert result.tasks == tasks


def test_load_warns_on_older_schema_version(tmp_path, tasks):
    """A schema from an older version of the app should load but warn, not discard data."""
    json_file = tmp_path / "tasks.json"
    _write_payload(json_file, schema_version=0, tasks=tasks)

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.OK
    assert result.found_schema_version == 0
    assert result.schema_mismatch is True
    assert result.tasks == tasks


def test_load_warns_on_app_version_mismatch(tmp_path, tasks):
    """A file saved by a different EasyDone release should load but warn."""
    json_file = tmp_path / "tasks.json"
    _write_payload(json_file, app_version="0.0.1-not-current", tasks=tasks)

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.OK
    assert result.found_app_version == "0.0.1-not-current"
    assert result.app_mismatch is True
    assert result.tasks == tasks


def test_load_app_version_mismatch_dont_overrides_schema_warning_message(tmp_path, tasks):
    """
    If both schema and app versions mismatches then both warnings should be recorded in the msg.
    """
    json_file = tmp_path / "tasks.json"
    _write_payload(
        json_file,
        schema_version=CURRENT_SCHEMA_VERSION + 1,
        app_version="0.0.1-not-current",
        tasks=tasks,
    )

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.OK
    assert result.found_app_version == "0.0.1-not-current"
    assert result.found_schema_version == CURRENT_SCHEMA_VERSION + 1
    assert result.app_mismatch is True
    assert result.schema_mismatch is True
    assert result.tasks == tasks


# ================================================================
# NEW TESTS: Backup (save) and Quarantine (load) behavior
# These cover the refactored _backup() and its integration
# ================================================================

def test_save_creates_backup_and_returns_dict_with_path_when_file_exists(tmp_path, tasks):
    """If tasks.json already exists, save() should:
    - Copy it to tasks.json.bak
    - Return a dict with backup_path set (and backup_exception None)
    - Write the new data to the main file
    """
    json_file = tmp_path / "tasks.json"
    initial_content = {"some": "old data"}
    json_file.write_text(json.dumps(initial_content), encoding="utf-8")

    handler = JSONHandler(str(json_file))
    save_result = handler.save(tasks)

    # Backup exists and contains the old content
    backup_file = json_file.with_suffix(json_file.suffix + ".bak")
    assert backup_file.exists()
    assert json.loads(backup_file.read_text(encoding="utf-8")) == initial_content

    # Main file contains the new tasks
    saved_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert saved_data["tasks"] == tasks

    # save() returns dict with backup_path set, no exception
    assert save_result["backup_path"] == backup_file
    assert save_result["backup_exception"] is None


def test_save_returns_dict_with_none_path_and_exception_when_file_does_not_exist(tmp_path, tasks):
    """If tasks.json does not exist, save() should:
    - NOT create a .bak file (copy2 raises FileNotFoundError)
    - Return a dict with backup_path=None and backup_exception set to FileNotFoundError
    - Still write the main file correctly
    """
    json_file = tmp_path / "tasks.json"
    assert not json_file.exists()

    handler = JSONHandler(str(json_file))
    save_result = handler.save(tasks)

    backup_file = json_file.with_suffix(json_file.suffix + ".bak")
    assert not backup_file.exists()

    saved_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert saved_data["tasks"] == tasks

    assert save_result["backup_path"] is None
    assert isinstance(save_result["backup_exception"], FileNotFoundError)


def test_save_backup_failure_does_not_block_write_and_returns_dict_with_exception(tmp_path, tasks, monkeypatch):
    """If shutil.copy2 fails during backup (e.g. PermissionError), save() should:
    - Still write the main file
    - NOT leave a partial .bak file behind
    - Return a dict with backup_path=None and backup_exception set to the caught error
    """
    json_file = tmp_path / "tasks.json"
    initial_content = {"some": "old data"}
    json_file.write_text(json.dumps(initial_content), encoding="utf-8")

    # Mock copy2 to raise PermissionError
    def failing_copy(*args, **kwargs):
        raise PermissionError("Forbidden")

    monkeypatch.setattr(shutil, "copy2", failing_copy)

    handler = JSONHandler(str(json_file))
    save_result = handler.save(tasks)

    # Main file is still written correctly
    saved_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert saved_data["tasks"] == tasks

    # No .bak file should exist (the failed copy should be cleaned up)
    backup_file = json_file.with_suffix(json_file.suffix + ".bak")
    assert not backup_file.exists()

    # save() returns dict with backup_path=None and the caught exception
    assert save_result["backup_path"] is None
    assert isinstance(save_result["backup_exception"], PermissionError)


def test_load_corrupted_file_quarantine_failure_returns_backup_path_none(tmp_path, monkeypatch):
    """If copying the corrupted file to quarantine fails, load() should:
    - NOT crash
    - Still return status CORRUPTED
    - Set backup_path to None
    - Return empty tasks
    """
    json_file = tmp_path / "tasks.json"
    json_file.write_text("{not valid", encoding="utf-8")

    # Mock copy2 to raise PermissionError
    def failing_copy(*args, **kwargs):
        raise PermissionError("Forbidden")

    monkeypatch.setattr(shutil, "copy2", failing_copy)

    handler = JSONHandler(str(json_file))
    result = handler.load()

    assert result.status is LoadStatus.CORRUPTED
    assert result.tasks == {}
    assert result.backup_path is None

    # Original file still exists
    assert json_file.exists()