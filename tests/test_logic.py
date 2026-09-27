"""Unit tests for task creation, updates, filtering, sorting, and statistics."""

from datetime import date, datetime, timedelta

import pytest

from easydone.logic import Stats, TasksManager, normalize_due_date


def test_new_tasks_start_with_empty_tags(empty_manager):
    empty_manager.new("test")

    task = next(iter(empty_manager.tasks.values()))
    assert task["tags"] == []


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

    assert manager.update("123", add_tags=["urgent", "work"], remove_tags=["work"]) is True
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
        manager.update_many(["123", "456"], new_prior="normal")

    assert manager.tasks["123"]["priority"] == "low"
    assert manager.tasks["456"]["priority"] == "normal"


def test_stats_returns_correct_values(manager):
    manager.tasks["123"]["due"] = (datetime.now() - timedelta(days=1)).date().isoformat()
    manager.tasks["456"]["due"] = (datetime.now() + timedelta(days=3)).date().isoformat()

    stats = manager.stats()

    assert isinstance(stats, Stats)
    assert stats.total_tasks == 3
    assert stats.total_by_priority == {"low": 1, "normal": 1, "high": 0, "urgent": 1}
    assert stats.total_by_status == {"not-done": 1, "in-progress": 1, "done": 1}
    assert stats.total_overdue == 1
    assert stats.total_near_overdue == 1


def test_list_sorts_tasks_by_supported_fields(manager):
    assert manager.list(sort_by="status") == ["123", "111", "456"]
    assert manager.list(sort_by="status", reverse=True) == ["456", "111", "123"]
    assert manager.list(sort_by="priority") == ["123", "456", "111"]
    assert manager.list(sort_by="priority", reverse=True) == ["111", "456", "123"]
    assert manager.list(sort_by="created") == ["456", "123", "111"]
    assert manager.list(sort_by="created", reverse=True) == ["111", "123", "456"]
    assert manager.list(sort_by="updated") == ["456", "111", "123"]
    assert manager.list(sort_by="updated", reverse=True) == ["123", "111", "456"]
