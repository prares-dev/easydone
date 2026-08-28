import json
import os
import sys
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, NamedTuple, Any
from enum import Enum

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
    - The final file is placed under <base>/easydone/tasks.json so the data is predictable and independent of the current working directory.
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
    return base_dir / "easydone" / "tasks.json"

class LoadStatus(Enum):
    OK = "ok"
    MISSING = "missing"
    CORRUPTED = "corrupted"

class LoadingResult(NamedTuple):
    tasks: dict[str, dict] = {}
    status: LoadStatus = LoadStatus.OK
    file_path: Optional[Path] = None
    backup_path: Optional[Path] = None
    backup_exception: Optional[Exception] = None
    found_schema_version: Optional[int] = None
    found_app_version: Optional[str] = None
    schema_mismatch: bool = False
    app_mismatch: bool = False

class JSONHandler():
    def __init__(self, json_file: Optional[str] = None):
        """
        Initialize a storage handler with a stable absolute data file path.
        """
        self.app_version = __version__
        self.json_file = Path(json_file).expanduser() if json_file else default_storage_path()

    def _quarantine_path(self) -> Path:
        """ Returns a quarantine path. """
        file_path = self.json_file
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        quarantine_path = file_path.with_name(
            f"{file_path.stem}.corrupted-{timestamp}{file_path.suffix}"
        )
        return quarantine_path
    
    def _backup_path(self) -> Path:
        """ Returns a backup path. """
        file_path = self.json_file
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        return backup_path
    
    def _backup(self, quarantine=False) -> dict[str, Any]:
        """
        Backups a file, returns the backup path if succeed, else returns the exception raised.
        """
        try:
            file_path = self.json_file
            backup_path = self._quarantine_path() if quarantine else self._backup_path()
            shutil.copy2(file_path, backup_path)
            return {"backup_path": backup_path, "backup_exception": None}
        except (PermissionError, MemoryError, FileNotFoundError) as exc:
            # remove backup file if any error happened
            backup_path.unlink(missing_ok=True) # type: ignore
            return {"backup_path": None, "backup_exception": exc}

    def load(self) -> LoadingResult:
        """Load tasks from the JSON file."""
        # load file's content into payload or handle exception
        try:
            with open(self.json_file, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except FileNotFoundError:
            return LoadingResult(
                tasks={}, status=LoadStatus.MISSING, file_path=self.json_file
                )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            backup_result = self._backup(quarantine=True)
            return LoadingResult(
                tasks={}, status=LoadStatus.CORRUPTED, 
                file_path=self.json_file, **backup_result
                )

        # unexpected format of content loaded
        if not isinstance(payload, dict):
            backup_result = self._backup(quarantine=True)
            return LoadingResult(
                tasks={}, status=LoadStatus.CORRUPTED, 
                file_path=self.json_file, **backup_result
                )

        # try to get metadata from dict loaded
        tasks = payload.get("tasks")
        schema_version = payload.get("schema_version", 0)
        app_version = payload.get("app_version", "unknown")

        # unexpected format of tasks
        if not isinstance(tasks, dict):
            backup_result = self._backup(quarantine=True)
            return LoadingResult(
                tasks={}, status=LoadStatus.CORRUPTED, 
                file_path=self.json_file, **backup_result
                )

        return LoadingResult(
            tasks=tasks, status=LoadStatus.OK, file_path=self.json_file,
            found_schema_version = schema_version,
            found_app_version = app_version,
            schema_mismatch = schema_version != CURRENT_SCHEMA_VERSION,
            app_mismatch = app_version != self.app_version
            )

    def save(self, tasks: dict[str, dict]) -> dict[str, Any]:
        """Persist tasks with metadata so upgrades can be reviewed safely. Returns a dict containing backup results."""
        if not isinstance(tasks, dict):
            raise TypeError("tasks must be a dictionary of task records")

        self.json_file.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "app_version": self.app_version,
            "saved_at": datetime.now().date().isoformat(),
            "tasks": tasks,
        }

        # Keep the last known-good file before touching it.
        backup_result = self._backup()
    
        # Write to a temp file in the SAME directory (matters: os.replace across
        # filesystems isn't atomic), then swap it in as one step.
        fd, tmp_path = tempfile.mkstemp(
            dir=self.json_file.parent, prefix=".tasks-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(payload, tmp_file, indent=4)
            os.replace(tmp_path, self.json_file)  # atomic on POSIX AND Windows
        except Exception:
            os.unlink(tmp_path)  # don't leave stray .tmp files on failure
            raise
        
        return backup_result