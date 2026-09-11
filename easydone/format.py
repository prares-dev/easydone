"""Output formatting helpers.

This module centralizes all user-facing presentation logic.
It uses Rich when available, otherwise falls back to plain text.
"""

from __future__ import annotations

import hashlib
from typing import Any, TypedDict

from . import __version__
from .logic import Stats, is_near_overdue, is_overdue
from .storage import CURRENT_SCHEMA_VERSION, LoadingResult, LoadStatus

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
    style: str | None


# ----------------------------------------------------------------------------
# Rich availability
# ----------------------------------------------------------------------------

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

_console = Console() if RICH_AVAILABLE else None  # type: ignore

PRIORITY_STYLES = {
    "low": "dim",
    "normal": "",
    "high": "bold yellow",
    "urgent": "bold red",
}
STATUS_STYLES = {
    "not-done": "dim",
    "in-progress": "cyan",
    "done": "green",
}

TAG_STYLES = (
    "bright_blue",
    "bright_cyan",
    "bright_green",
    "bright_magenta",
    "bright_yellow",
    "bright_red",
    "bright_white",
    "cyan",
    "green",
    "magenta",
)

SEMANTIC_TAG_STYLES = {
    "bug": "bold red",
    "feature": "bold green",
    "personal": "bright_magenta",
    "work": "bright_blue",
}


def tag_style(tag: str) -> str:
    """Return a stable Rich style for a tag value."""
    semantic_style = SEMANTIC_TAG_STYLES.get(tag.casefold())
    if semantic_style:
        return semantic_style
    digest = hashlib.sha256(tag.encode("utf-8")).digest()
    style_index = int.from_bytes(digest[:4], "big") % len(TAG_STYLES)
    return TAG_STYLES[style_index]


# ----------------------------------------------------------------------------
# Core rendering helpers
# ----------------------------------------------------------------------------


def _print(text: str, style: str | None = None) -> None:
    """Print a single piece of text with optional styling if Rich is available.

    This is for simple messages that are just one string with one style.

    Example:
        _print("Tasks loaded successfully.", style="green")
    """
    if RICH_AVAILABLE:
        _console.print(Text(text, style=style))  # type: ignore
    else:
        print(text)


def _render_parts(parts: list[MyText], return_val: bool = False) -> str | Text | None:
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
        text_obj = Text("")  # type: ignore
        for part in parts:
            text_obj.append(part.get("text", ""), style=part.get("style"))
        if return_val:
            return text_obj
        _console.print(text_obj)  # type: ignore
    else:
        result = "".join(part.get("text", "") for part in parts)
        if return_val:
            return result
        print(result)


def _plain_table(tasks: dict[str, dict], ids: list[str], no_dates: bool) -> None:
    """Plain text table renderer."""
    print("┌────────────────────────┐")
    print("│ EASYDONE: Task Tracker |")
    print("└────────────────────────┘")
    for task_id in ids:
        task = tasks[task_id]
        desc = task.get("description", "-")
        prior = task.get("priority", "-")
        stat = task.get("status", "-")
        tags = task.get("tags", [])
        tag_text = " ".join(f"[{tag}]" for tag in tags) or "-"

        print(f'┌─ ID: {task_id} ... "{desc}"')
        print(f"│  ├── Priority: {prior}")
        print(f"│  ├── Status: {stat}")
        print(f"│  {'├──' if not no_dates else '└──'} Tags: {tag_text}")

        if not no_dates:
            create = task.get("created-at", "-")
            due = task.get("due", "-")
            due = "-" if due is None else due
            update = task.get("updated-at", "-")
            update = "-" if update is None else update

            print(f"│  ├── Due: {due}")
            print(f"│  ├── Created at: {create}")
            print(f"│  └── Updated at: {update}")


def _rich_table(tasks: dict[str, dict], ids: list[str], no_dates: bool) -> None:
    """Rich table renderer."""
    table = Table(  # type: ignore
        show_header=True,
        header_style="bold white",
        show_lines=True,
        box=box.SIMPLE_HEAD,  # type: ignore
    )  # type: ignore
    table.add_column("ID", header_style="gold1", style="gold1", no_wrap=True, justify="center")
    table.add_column(
        "Description",
        header_style=" white",
        style="italic white",
        min_width=30,
        overflow="fold",
    )
    table.add_column("Tags", overflow="fold")
    table.add_column("Priority", no_wrap=True, justify="center")
    table.add_column("Status", no_wrap=True, justify="center")
    if not no_dates:
        table.add_column("Due", no_wrap=True, justify="center")
        table.add_column(":date:Created", no_wrap=True, justify="center")
        table.add_column(":pencil:Updated", no_wrap=True, justify="center")

    def due_style(task: dict) -> str:
        if is_overdue(task):
            return "bold red"
        elif is_near_overdue(task):
            return "bright_yellow"
        else:
            return "dim"

    for task_id in ids:
        task = tasks[task_id]
        desc = task.get("description", "-")
        prior = task.get("priority", "-")
        stat = task.get("status", "-")
        tags = task.get("tags", [])

        description_text = Text(desc, overflow="ellipsis")  # type: ignore
        tags_text = Text("")  # type: ignore
        if tags:
            for index, tag in enumerate(tags):
                if index:
                    tags_text.append(" ")
                tags_text.append(f"[{tag}]", style=tag_style(tag))
        else:
            tags_text.append("-")

        if not no_dates:
            create = task.get("created-at", "-")
            due = task.get("due", "-")
            due = "-" if due is None else due
            update = task.get("updated-at", "-")
            update = "-" if update is None else update

            table.add_row(
                task_id,
                description_text,  # type: ignore
                tags_text,  # type: ignore
                Text(prior, style=PRIORITY_STYLES.get(prior, "")),  # type: ignore
                Text(stat, style=STATUS_STYLES.get(stat, "")),  # type: ignore
                Text(due, style=due_style(task)),  # type: ignore
                create,
                update,
            )
        else:
            table.add_row(
                task_id,
                description_text,  # type: ignore
                tags_text,  # type: ignore
                Text(prior, style=PRIORITY_STYLES.get(prior, "")),  # type: ignore
                Text(stat, style=STATUS_STYLES.get(stat, "")),  # type: ignore
            )

    _console.print(table)  # type: ignore


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def print_table(tasks: dict[str, dict], ids: list[str], no_dates: bool = False) -> None:
    """Render a task table with Rich or plain text fallback."""
    if not ids:
        message = "No tasks exist." if not tasks else "No tasks match the selected filters."
        _print(message, style="yellow")
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
            f"written by EasyDone {result.found_app_version} (running Easydone {__version__})"
        )

    if lines:
        msg = "Warning: " + " and ".join(lines) + "."

    if msg:
        _print(msg, style="yellow")
    else:
        _print("Tasks loaded successfully.", style="green")


def report_backup(backup_result: dict[str, Any]) -> None:
    """Report whether a backup succeeded or failed."""
    if backup_result["backup_path"]:
        _print("Backup succesfully done", style="green")
    else:
        _print(
            f"Warning: Couldn't backup ({backup_result['backup_exception']})",
            style="yellow",
        )


def confirm_deletion(task_id: str, description: str, max_attempts: int = 3) -> bool:
    """Ask the user for confirmation with styled prompt using MyText parts."""
    attempts = 0

    # Build the prompt once – as a list of MyText parts
    prompt_parts: list[MyText] = [
        {"text": "Are you sure about deleting task "},
        {"text": f'{task_id}: "{description}"', "style": "yellow"},
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

        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            _render_parts(
                [
                    {"text": "Invalid input. ", "style": "red"},
                    {"text": "Please enter '"},
                    {"text": "y", "style": "yellow"},
                    {"text": "' or 'n'."},
                ]
            )
            attempts += 1

    _render_parts(
        [
            {
                "text": f"Unable to get valid user response after {max_attempts} attempts. Aborting deletion attempt...",  # ruff: ignore[E501]
                "style": "yellow",
            }
        ]
    )
    return False


def print_stats(stats: Stats) -> None:
    if not stats.total_tasks:
        _print("Empty tasks", style="yellow")
        return

    _print("\nYour EasyDone stats: ", style="bold magenta")
    total = stats.total_tasks
    _render_parts(
        [
            MyText(text="• You have ", style="bold white"),
            MyText(
                text=f"{total} task{'s' if total > 1 else ''} ",
                style="blue",
            ),
            MyText(text="registered in total.", style="bold white"),
        ]
    )

    _print("• Totals by priority:", style="bold white")
    for p, t in stats.total_by_priority.items():
        _render_parts([MyText(text=f"\t{p}: ", style=PRIORITY_STYLES[p]), MyText(text=f"{t}")])
    _print("• Totals by status:", style="bold white")
    for s, t in stats.total_by_status.items():
        _render_parts([MyText(text=f"\t{s}: ", style=STATUS_STYLES[s]), MyText(text=f"{t}")])

    overdue = stats.total_overdue
    _render_parts(
        [
            MyText(text="• You have ", style="bold white"),
            MyText(text=f"{overdue} overdue ", style="bold red"),
            MyText(text=f"task{'s' if overdue > 1 else ''}.", style="bold white"),
        ]
    )

    near_overdue = stats.total_near_overdue
    _render_parts(
        [
            MyText(text="• You have ", style="bold white"),
            MyText(text=f"{near_overdue} near overdue ", style="bold yellow"),
            MyText(text=f"task{'s' if near_overdue > 1 else ''}.", style="bold white"),
        ]
    )
