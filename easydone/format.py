"""Output formatting helpers.

This module centralizes all user-facing presentation logic so the CLI
parsing and task-management logic remain separate. The primary function
`print_table` prints a table of tasks. It attempts to use Rich for nicely
styled tables and colors; when Rich is not available it falls back to a
plain-text table so the application remains dependency-light.
"""

from typing import Dict, List, Any
from .storage import LoadingResult, LoadStatus, CURRENT_SCHEMA_VERSION
from . import __version__

try:
    # Import the specific Rich helpers we need. If they are not available,
    # the import will raise and the code will fall back to plain text.
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False


def _plain_print(tasks: Dict[str, dict], 
                ids: List[str], 
                no_dates: bool = False
                ) -> None:
    """Plain-text fallback used when Rich is unavailable."""
    
    if not tasks:
        print("No tasks to show.")
        return
    
    print("\n│easydone: task tracker")
    print("├──────────────────────")
    for task_id in ids:
        # Use .get() so older or partially missing task dictionaries still print.
        task = tasks[task_id]
        desc = task.get('description', 'unknown')
        prior = task.get('priority', 'unknown')
        stat = task.get('status', 'unknown')
        create = task.get('created-at', 'unknown')
        update = task.get('updated-at')
        update = '-' if update is None else update
        
        print(f"├── ID: {task_id} ... \"{desc}\"")
        print(f"│    ├── Priority: {prior}")
        print(f"│    {"├──" if not no_dates else "└──"} Status: {stat}")
        if not no_dates:
            print(f"│    ├── Created at: {create}")
            print(f"│    └── Updated at: {update}")

def print_table(tasks: Dict[str, dict], 
                ids: List[str], 
                no_dates: bool = False
                ) -> None:
    """Print a tasks table using Rich when available, otherwise use plain text.

    Columns: ID, Description, Priority, Status, Created, Updated.
    The status and priority values are highlighted in color when Rich is present.
    """
    if not ids:
        print("No tasks to show.")
        return

    if not RICH_AVAILABLE:
        _plain_print(tasks, ids, no_dates=no_dates)
        return

    # Build a Rich table in the presentation layer. This keeps formatting and
    # colors separated from task logic and CLI argument parsing.
    console = Console() # type: ignore
    table = Table(show_header=True, header_style="bold magenta") # type: ignore
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Description")
    table.add_column("Priority", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    if not no_dates:
        table.add_column("Created", no_wrap=True)
        table.add_column("Updated", no_wrap=True)

    priority_styles = {
        "low": "dim",
        "normal": "",
        "high": "bold yellow",
        "urgent": "bold red",
    }
    status_styles = {
        "not-done": "yellow",
        "in-progress": "cyan",
        "done": "green",
    }

    for task_id in ids:
        task = tasks[task_id]
        desc = task.get('description', 'unknown')
        prior = task.get('priority', 'unknown')
        stat = task.get('status', 'unknown')
        create: str
        update: str
        if not no_dates:
            create = task.get('created-at', 'unknown')
            update = task.get('updated-at', 'unknown')
            update = '-' if update is None else update
            table.add_row(
                task_id,
                Text(desc, overflow='ellipsis'),    # type: ignore
                Text(prior, style=priority_styles.get(prior, "")),  # type: ignore
                Text(stat, style=status_styles.get(stat, "")),  # type: ignore
                create,
                update,
            )
        else:
            table.add_row(
                task_id,
                Text(desc, overflow='ellipsis'),    # type: ignore
                Text(prior, style=priority_styles.get(prior, "")),  # type: ignore
                Text(stat, style=status_styles.get(stat, "")),  # type: ignore
            )
            
    console.print(table)

def describe_load_result(result: LoadingResult) -> None:
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
        style = 'yellow'
    else:
        style = 'green'
        msg = "Tasks loaded successfully."
    
    if RICH_AVAILABLE:
        console = Console()                     # type: ignore
        console.print(Text(msg, style=style))   # type: ignore
    else:
        print(msg)

def report_backup(backup_result: dict[str, Any]):
    if backup_result['backup_path']:
        text = "Backup succesfully done"
        style = 'green'
    else:
        text = f"Warning: Couldn't backup ({backup_result['backup_exception']})"
        style = 'yellow'
    if RICH_AVAILABLE:
        console = Console()     # type: ignore
        console.print(Text(text=text, style=style)) # type: ignore
    else:
        print(text)

def confirm_deletion(id: int, description: str, max_attempts: int = 3) -> bool:
    """Asks the user a yes/no question and returns True for yes and False for no."""
    plain_prompt = f'Are you sure about deleting task {id}: "{description}" ? (y/n): '

    if RICH_AVAILABLE:
        console = Console()                                                             # type: ignore
        rich_prompt = (
            Text("Are you sure about deleting task ")                                   # type: ignore
            + Text(f"{id}: \"{description}\"", 'yellow')                                # type: ignore
            + Text(' (') + Text('y', 'yellow') + Text('/n): ')                          # type: ignore
        )

    attempts = 0
    while attempts < max_attempts:
        if RICH_AVAILABLE:
            console.print(rich_prompt)                                                  # type: ignore
        else:
            print(plain_prompt)

        try:
            response = input().strip().lower()
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                console.print(Text("aborting deletion attempt...", "yellow"))           # type: ignore
            else:
                print("aborting deletion attempt...")
            raise

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            if RICH_AVAILABLE:
                err1 = Text("Invalid input.", 'red')                                    # type: ignore
                err2 = Text("Please enter '") + Text('y', 'yellow') + Text("' or 'n'.") # type: ignore
                console.print(err1, err2)                                               # type: ignore
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
            attempts += 1

    msg = f"Unable to get valid user response after {max_attempts} attempts. Aborting deletion attempt..."
    if RICH_AVAILABLE:
        console.print(Text(msg, 'yellow'))                                              # type: ignore
    else:
        print(msg)
    return False