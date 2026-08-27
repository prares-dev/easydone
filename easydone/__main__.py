from .cli import Parser
from .logic import TasksManager
from .storage import JSONHandler
from .format import describe_load_result, report_backup_err

def main() -> None:
    # JSONHandler instance for load/save in .json.
    handler = JSONHandler()
    load_result = handler.load()
    describe_load_result(load_result)
    
    # TasksManager instance based on tasks loaded
    manager = TasksManager(tasks_from_file=load_result.tasks)
    
    # Parser instance for cli interface and argumments
    cli = Parser(manager)
    mutated = cli.start_parsing()
    
    # save tasks before exiting only if mutated status
    if mutated:
        backup_done = handler.save(manager.tasks)
        if backup_done: report_backup_err()

if __name__ == "__main__":
    main()