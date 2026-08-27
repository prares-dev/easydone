from .cli import Parser
from .logic import TasksManager
from .storage import JSONHandler

def main() -> None:
    # JSONHandler instance for load/save in .json.
    handler = JSONHandler()
    loading_result = handler.load()

    if loading_result.corrupted:
        print(loading_result.msg)
        # Handle corruption with backup
    elif loading_result.warning:
        print(loading_result.msg)
        # Handle warnings

    # TasksManager instance based on tasks loaded
    manager = TasksManager(tasks_from_file=loading_result.tasks)
    
    # Parser instance for cli interface and argumments
    cli = Parser(manager)
    mutated = cli.start_parsing()
    
    if mutated:
        # save tasks before exiting
        handler.save(manager.tasks)

if __name__ == "__main__":
    main()