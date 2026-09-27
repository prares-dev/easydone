"""Shared fixtures for task logic and CLI integration tests."""

from datetime import datetime, timedelta

import pytest

from easydone.logic import TasksManager


@pytest.fixture
def manager() -> TasksManager:
    """Manager with three tasks used by logic and CLI tests."""
    now = datetime.now()
    return TasksManager(
        {
            "123": {
                "description": "read a book",
                "status": "not-done",
                "priority": "low",
                "created-at": (now + timedelta(days=3)).date().isoformat(),
                "updated-at": (now + timedelta(days=9)).date().isoformat(),
            },
            "456": {
                "description": "write code",
                "status": "done",
                "priority": "normal",
                "created-at": now.date().isoformat(),
                "updated-at": (now + timedelta(days=4)).date().isoformat(),
            },
            "111": {
                "description": "go supermarket",
                "status": "in-progress",
                "priority": "urgent",
                "created-at": (now + timedelta(days=5)).date().isoformat(),
                "updated-at": (now + timedelta(days=7)).date().isoformat(),
            },
        }
    )


@pytest.fixture
def empty_manager() -> TasksManager:
    return TasksManager({})
