import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, NamedTuple

from . import __version__

CURRENT_SCHEMA_VERSION = 1


def default_storage_path() -> Path:
    """Return a stable, user-scoped path for EasyDone task data.

    Behavior and rationale:
    - If the EASYDONE_DATA_FILE environment variable is set, use it. This allows CI, tests, and advanced users to redirect storage to a custom file.
    - Otherwise choose a platform-appropriate per-user application data directory:
        * Windows: %APPDATA% (e.g. C:/Users/<user>/AppData/Roaming)
        * macOS: ~/Library/Application Support
        * Linux/other: XDG_DATA_HOME or ~/.local/share as a fallback
    - The final file is placed under <base>/easydone-task-tracker/tasks.json so the data is predictable and independent of the current working directory.
    """
    # Allow an explicit override for testing or advanced usage. Expand ~ if present.
    custom_path = os.environ.get("EASYDONE_DATA_FILE")
    if custom_path:
        return Path(custom_path).expanduser()

    # Select a sensible base directory depending on the platform. Using a
    # per-user application data directory avoids scattering data files across
    # arbitrary working directories and follows common OS conventions.
    if os.name == "nt":
        # On Windows prefer APPDATA; fall back to a reasonable user path when
        # APPDATA is not available in the environment.
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        # macOS convention for app data
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        # Follow XDG Base Directory Specification when possible, otherwise use
        # ~/.local/share as a conventional fallback for Linux and other Unix-like OSes.
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    # Keep the final data file path deterministic and easy to locate.
    return base_dir / "easydone-task-tracker" / "tasks.json"


class LoadingResult(NamedTuple):
    corrupted: bool = False
    warning: bool = False
    msg: str = "Loading task succesfully completed..."
    tasks: dict[str, dict] = {}

class JSONHandler():
    def __init__(self, json_file: Optional[str] = None):
        """Initialize a storage handler with a stable absolute data file path."""
        self.app_version = __version__
        self.json_file = Path(json_file).expanduser() if json_file else default_storage_path()

    def _warn_msg_version_mismatch(self, schema_version: int, app_version: str) -> Optional[str]:
        """Warn when a file was created by a different app or data schema."""
        warning_msg = None
        
        if schema_version > CURRENT_SCHEMA_VERSION:
            warning_msg = ( f"Warning: {self.json_file} was created with a newer data schema "
                            f"({schema_version}) than this app supports ({CURRENT_SCHEMA_VERSION}). Review task data before saving." )
            
        elif schema_version < CURRENT_SCHEMA_VERSION:
            warning_msg = ( f"Warning: {self.json_file} uses an older data schema ({schema_version}). "
                            f"This app expects version {CURRENT_SCHEMA_VERSION}. Review task data before saving." )
            
        if app_version and app_version != self.app_version:
            warning_msg = ( f"Warning: {self.json_file} was written by EasyDone {app_version}, while "
                            f"this session is running {self.app_version}. Review task data before saving.")

        return warning_msg

    def load(self) -> LoadingResult:
        """Load tasks from the JSON file."""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except FileNotFoundError:
            msg = f"{self.json_file} does not exist. Starting with empty task list..."
            return LoadingResult(msg=msg, tasks={})
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            msg = f"{self.json_file} is unreadable or malformed. Starting with empty task list..."
            return LoadingResult(corrupted=True, msg=msg, tasks={})

        if not isinstance(payload, dict):
            msg = f"{self.json_file} does not contain a task dictionary."
            return LoadingResult(corrupted=True, msg=msg, tasks={})

        tasks = payload.get("tasks")
        schema_version = payload.get("schema_version", 0)
        app_version = payload.get("app_version", "unknown")

        if not isinstance(tasks, dict):
            msg = f"Warning: {self.json_file} is missing a valid tasks payload. Starting with empty task list..."
            return LoadingResult(corrupted=True, msg=msg, tasks={})

        warn_msg = self._warn_msg_version_mismatch(schema_version, app_version)
        if warn_msg:
            return LoadingResult(warning=True, msg=warn_msg, tasks=tasks)
        else:
            return LoadingResult(tasks=tasks)

    def save(self, tasks: dict[str, dict]) -> None:
        """Persist tasks with metadata so upgrades can be reviewed safely."""
        if not isinstance(tasks, dict):
            raise TypeError("tasks must be a dictionary of task records")

        self.json_file.parent.mkdir(parents=True, exist_ok=True)

        # Record only the date (YYYY-MM-DD) to keep the saved_at field
        # human-readable and easier to compare in the UI or logs. Storing
        # date-only avoids timezone/microsecond details that are unnecessary
        # for this application's needs.
        payload = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "app_version": self.app_version,
            "saved_at": datetime.now().date().isoformat(),
            "tasks": tasks,
        }

        with open(self.json_file, 'w', encoding='utf-8') as file:
            json.dump(payload, file, indent=4)
