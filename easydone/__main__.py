from .cli import CLIApp
from .storage import JSONHandler

def main() -> None:
    # JSONHandler instance for load/save in .json.
    json_handler = JSONHandler()
    # load tasks
    tasks = json_handler.load()
    
    # CLIApp instance for argument parsing related logic.
    # based on tasks loaded
    cli = CLIApp(tasks)
    cli.start_parsing()
    
    # save tasks before exiting
    json_handler.save(cli.tasks_manager.tasks)


if __name__ == "__main__":
    main()