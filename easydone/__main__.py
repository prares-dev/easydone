from .cli import Parser
from .logic import TasksManager
from .storage import JSONHandler

def main() -> None:
    # JSONHandler instance for load/save in .json.
    handler = JSONHandler()
    tasks = handler.load()

    # TasksManager instance based on tasks loaded
    manager = TasksManager(tasks_from_file=tasks)
    
    # Parser instance for cli interface and argumments
    cli = Parser(manager)
    cli.start_parsing()

    # save tasks before exiting
    handler.save(manager.tasks)

if __name__ == "__main__":
    main()