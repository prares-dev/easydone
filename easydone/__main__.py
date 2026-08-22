from .cli import CLIApp
from .storage import JSONHandler

def main() -> None:
    json_handler = JSONHandler()
    tasks = json_handler.load()
    cli = CLIApp(tasks)
    cli.start_parsing()
    json_handler.save(cli.tasks_manager.tasks)


if __name__ == "__main__":
    main()