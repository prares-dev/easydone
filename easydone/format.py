"""Output formatting helpers.

This module centralizes all user-facing presentation logic.
It uses Rich when available, otherwise falls back to plain text.
"""

from typing import Dict, List, Any, Optional, TypedDict
from .logic import time_to_due

from .storage import LoadingResult, LoadStatus, CURRENT_SCHEMA_VERSION
from . import __version__


# ----------------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------------

class MyText(TypedDict, total=False):
    """A piece of text with optional style information.

    Example:
        {"text": "Warning: ", "style": "yellow"}
        {"text": "file not found"}
    """
    text: str
    style: Optional[str]


# ----------------------------------------------------------------------------
# Rich availability
# ----------------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

_console = Console() if RICH_AVAILABLE else None # type: ignore


# ----------------------------------------------------------------------------
# Core rendering helpers
# ----------------------------------------------------------------------------

def _print(text: str, style: Optional[str] = None) -> None:
    """Print a single piece of text with optional styling if Rich is available.

    This is for simple messages that are just one string with one style.

    Example:
        _print("Tasks loaded successfully.", style="green")
    """
    if RICH_AVAILABLE:
        _console.print(Text(text, style=style))  # type: ignore
    else:
        print(text)

def _render_parts(parts: List[MyText]) -> None:
    """Render multiple styled text parts.

    If Rich is available, each part is rendered with its style.
    If not, all text is concatenated and printed plainly.

    This is useful for complex messages with multiple styled segments.

    Example:
        parts = [
            {"text": "Warning: ", "style": "yellow"},
            {"text": "Task not found", "style": "bold red"},
        ]
        _render_parts(parts)
    """
    if RICH_AVAILABLE:
        text_obj = Text() # type: ignore
        for part in parts:
            text_obj.append(part.get("text", ""), style=part.get("style"))
        _console.print(text_obj)  # type: ignore
    else:
        print("".join(part.get("text", "") for part in parts))

def _plain_table(tasks: Dict[str, dict], ids: List[str], no_dates: bool) -> None:
    """Plain text table renderer."""
    print("┌────────────────────────┐")
    print("│ EASYDONE: Task Tracker |")
    print("└────────────────────────┘")
    for task_id in ids:
        task = tasks[task_id]
        desc = task.get('description', '-')
        prior = task.get('priority', '-')
        stat = task.get('status', '-')
        create = task.get('created-at', '-')
        due = task.get('due', '-')
        due = '-' if due is None else due
        update = task.get('updated-at', '-')
        update = '-' if update is None else update

        print(f"┌─ ID: {task_id} ... \"{desc}\"")
        print(f"│  ├── Priority: {prior}")
        print(f"│  {'├──' if not no_dates else '└──'} Status: {stat}")
        if not no_dates:
            print(f"│  ├── Due: {due}")
            print(f"│  ├── Created at: {create}")
            print(f"│  └── Updated at: {update}")

def _rich_table(tasks: Dict[str, dict], ids: List[str], no_dates: bool) -> None:
    """Rich table renderer."""
    table = Table(show_header=True, header_style="bold magenta") # type: ignore
    table.add_column("ID", style="dim", no_wrap=True, justify="center")
    table.add_column("Description")
    table.add_column("Priority", no_wrap=True)
    table.add_column("Status", no_wrap=True, justify="center")
    if not no_dates:
        table.add_column("Due", no_wrap=True, justify="center")
        table.add_column("Created", no_wrap=True, justify="center")
        table.add_column("Updated", no_wrap=True, justify="center")

    priority_styles = {
        "low": "dim",
        "normal": "blue",
        "high": "bold yellow",
        "urgent": "bold red",
    }
    status_styles = {
        "not-done": "yellow",
        "in-progress": "cyan",
        "done": "green",
    }
    
    def due_style(task: dict) -> str:
        time = time_to_due(task)
        if not time:
            return ''
        
        if time.total_seconds() < 0:
            return "bold red"
        elif time.days < 5:
            return "yellow"
        else:
            return 'green'

    for task_id in ids:
        task = tasks[task_id]
        desc = task.get('description', '-')
        prior = task.get('priority', '-')
        stat = task.get('status', '-')

        if not no_dates:
            create = task.get('created-at', '-')
            due = task.get('due', '-')
            due = '-' if due is None else due
            update = task.get('updated-at', '-')
            update = '-' if update is None else update
            table.add_row(
                task_id,
                Text(desc, overflow='ellipsis'), # type: ignore
                Text(prior, style=priority_styles.get(prior, "")), # type: ignore
                Text(stat, style=status_styles.get(stat, "")), # type: ignore
                Text(due, style=due_style(task)),   # type: ignore
                create,
                update,
            )
        else:
            table.add_row(
                task_id,
                Text(desc, overflow='ellipsis'), # type: ignore
                Text(prior, style=priority_styles.get(prior, "")), # type: ignore
                Text(stat, style=status_styles.get(stat, "")), # type: ignore
            )

    _console.print(table)  # type: ignore


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def print_table(tasks: Dict[str, dict], ids: List[str], no_dates: bool = False) -> None:
    """Render a task table with Rich or plain text fallback."""
    if not ids:
        _print("No tasks to show.", style='yellow')
        return
    
    if not RICH_AVAILABLE:
        _plain_table(tasks, ids, no_dates)
    else:
        _rich_table(tasks, ids, no_dates)


def describe_load_result(result: LoadingResult) -> None:
    """Describe the result of loading a tasks file."""
    msg = ""
    if result.status is LoadStatus.MISSING:
        msg = f"{result.file_path} does not exist. Starting with an empty task list."

    if result.status is LoadStatus.CORRUPTED:
        msg = f"Warning: {result.file_path} is unreadable or malformed."
        if result.backup_path:
            msg += f" A copy was saved to {result.backup_path} for review."
        else:
            msg += f" Unable to save corrupted file: ({result.backup_exception})"

    lines = []
    if result.schema_mismatch:
        lines.append(
            f"Found schema version {result.found_schema_version} "
            f"(app expects {CURRENT_SCHEMA_VERSION})"
        )
    if result.app_mismatch:
        lines.append(
            f"written by EasyDone {result.found_app_version} "
            f"(running Easydone {__version__})"
        )

    if lines:
        msg = "Warning: " + " and ".join(lines) + "."

    if msg:
        _print(msg, style='yellow')
    else:
        _print("Tasks loaded successfully.", style='green')


def report_backup(backup_result: dict[str, Any]) -> None:
    """Report whether a backup succeeded or failed."""
    if backup_result['backup_path']:
        _print("Backup succesfully done", style='green')
    else:
        _print(f"Warning: Couldn't backup ({backup_result['backup_exception']})", style='yellow')


def confirm_deletion(task_id: str, description: str, max_attempts: int = 3) -> bool:
    """Ask the user for confirmation with styled prompt using MyText parts."""
    attempts = 0

    # Build the prompt once – as a list of MyText parts
    prompt_parts: List[MyText] = [
        {"text": "Are you sure about deleting task "},
        {"text": f"{task_id}: \"{description}\"", "style": "yellow"},
        {"text": " ("},
        {"text": "y", "style": "yellow"},
        {"text": "/n): "},
    ]

    while attempts < max_attempts:
        _render_parts(prompt_parts)

        try:
            response = input().strip().lower()
        except KeyboardInterrupt:
            _render_parts([{"text": "aborting deletion attempt...", "style": "yellow"}])
            raise

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            _render_parts([
                {"text": "Invalid input. ", "style": "red"},
                {"text": "Please enter '"},
                {"text": "y", "style": "yellow"},
                {"text": "' or 'n'."},
            ])
            attempts += 1

    _render_parts([
        {"text": f"Unable to get valid user response after {max_attempts} attempts. Aborting deletion attempt...", "style": "yellow"}
    ])
    return False