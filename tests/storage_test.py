import json

import pytest

from easydone.storage import JSONHandler


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


def test_load_returns_existing_tasks(tmp_path, tasks):
    json_file = tmp_path / "tasks.json"
    payload = {
        "schema_version": 1,
        "app_version": "0.1.0",
        "saved_at": "2026-08-24T00:00:00+00:00",
        "tasks": tasks,
    }

    json_file.write_text(json.dumps(payload), encoding="utf-8")

    handler = JSONHandler(str(json_file))

    assert handler.load() == tasks


def test_save_writes_tasks_to_json_file(tmp_path, tasks):
    json_file = tmp_path / "tasks.json"

    handler = JSONHandler(str(json_file))
    handler.save(tasks)

    saved_data = json.loads(json_file.read_text(encoding="utf-8"))

    assert saved_data["schema_version"] == 1
    assert saved_data["app_version"] == handler.app_version
    assert saved_data["tasks"] == tasks


def test_load_accepts_legacy_task_dictionary(tmp_path, tasks):
    json_file = tmp_path / "tasks.json"
    json_file.write_text(json.dumps(tasks), encoding="utf-8")

    handler = JSONHandler(str(json_file))

    assert handler.load() == tasks


def test_load_returns_empty_dict_when_file_is_missing(tmp_path):
    missing_file = tmp_path / "missing_tasks.json"

    handler = JSONHandler(str(missing_file))

    assert handler.load() == {}
    assert not missing_file.exists()
