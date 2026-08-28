from .cli import Parser
from .logic import TasksManager
from .storage import JSONHandler
from .format import describe_load_result, report_backup

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
        backup_result = handler.save(manager.tasks)
        report_backup(backup_result)

if __name__ == "__main__":
    main()