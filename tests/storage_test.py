import json

from easydone.storage import JSONHandler

def test_load_returns_existing_tasks(tmp_path):
    json_file = tmp_path / "tasks.json"
    expected = {
        "read a book": {"status": "not done"},
        "write code": {"status": "in progress"}
    }

    json_file.write_text(json.dumps(expected), encoding="utf-8")

    handler = JSONHandler(str(json_file))

    assert handler.load() == expected


def test_save_writes_tasks_to_json_file(tmp_path):
    json_file = tmp_path / "tasks.json"
    tasks = {
        "1": {"description": "read a book", "done": False},
    }

    handler = JSONHandler(str(json_file))
    handler.save(tasks)

    assert json.loads(json_file.read_text(encoding="utf-8")) == tasks


def test_load_returns_empty_dict_when_file_is_missing(tmp_path):
    missing_file = tmp_path / "missing_tasks.json"

    handler = JSONHandler(str(missing_file))

    assert handler.load() == {}
    assert not missing_file.exists()
