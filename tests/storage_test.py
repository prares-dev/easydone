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
            "updated-at": None
        },
        "722": {
            "description": "do house shores",
            "status": "not-done",
            "priority": "low",
            "created-at": "2026-08-22",
            "updated-at": "2026-08-22"
        }
    }

def test_load_returns_existing_tasks(tmp_path, tasks):
    json_file = tmp_path / "tasks.json"
    expected = tasks

    json_file.write_text(json.dumps(expected), encoding="utf-8")

    handler = JSONHandler(str(json_file))

    assert handler.load() == expected


def test_save_writes_tasks_to_json_file(tmp_path, tasks):
    json_file = tmp_path / "tasks.json"
    expected = tasks

    handler = JSONHandler(str(json_file))
    handler.save(expected)

    assert json.loads(json_file.read_text(encoding="utf-8")) == expected


def test_load_returns_empty_dict_when_file_is_missing(tmp_path):
    missing_file = tmp_path / "missing_tasks.json"

    handler = JSONHandler(str(missing_file))

    assert handler.load() == {}
    assert not missing_file.exists()
