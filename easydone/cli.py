import argparse
import logic

SUPPORTED_STATUS = ["not-done", "done", "in-progress"]
SUPPORTED_PRIORITIES = ["low", "normal", "high", "urgent"]

class CLIApp():
    """ A class to manage all the CLIApp features. """
    
    def __init__(self, tasks_from_file: dict[str, dict]) -> None:
        """Initialize the CLIApp attributes"""
        self.tasks_manager = logic.TasksManager(tasks_from_file)
        self.build_parser()
    
    def build_parser(self) -> None:
        """ Create the main parser and sub-commands. """
        self.main_parser = argparse.ArgumentParser(
            prog = "EasyDone",
            description = "Task-Tracker. Create, delete, edit, do.",
            epilog = "Thanks for using %(prog)s! :)\nAll feedback is appreciated.",
            allow_abbrev = False # disable auto option abbreviation
        )
        
        # Sub-commands parser
        self.actions_subparser = self.main_parser.add_subparsers(
            title="actions", 
            help="Supported commands.")
        
        # 'NEW' command
        # ====================
        self.new_task_parser = self.actions_subparser.add_parser(
            "new", 
            help="Create a new task")
        
        self.new_task_parser.add_argument(
            "description", 
            type=str, 
            help="Description of the task to be added.")
        
        self.new_task_parser.add_argument(
            "-s",
            "--status", 
            type=str, 
            help="Optional initial status: defaults to 'not-done'.",
            choices=SUPPORTED_STATUS,
            default=SUPPORTED_STATUS[0])
        
        self.new_task_parser.add_argument(
            "-p",
            "--priority", 
            type=str, 
            help="Optional priority: defaults to 'low'.",
            choices=SUPPORTED_PRIORITIES,
            default=SUPPORTED_PRIORITIES[0])
        
        self.new_task_parser.set_defaults(func=self.tasks_manager.new)
        
        # 'UPDATE' command
        # ====================
        self.update_task_parser = self.actions_subparser.add_parser(
            "update", 
            help="Update a task.",
            argument_default=argparse.SUPPRESS)
        
        self.update_task_parser.add_argument(
            "id",
            type=str, 
            help="ID of the task to be updated.")
        
        self.update_task_parser.add_argument(
            "-d",
            "--description", 
            metavar="new-description",
            type=str, 
            help="Update description.")
        
        self.update_task_parser.add_argument(
            "-p",
            "--priority", 
            metavar="new-priority",
            type=str, 
            help="Update priority.")
        
        self.update_task_parser.set_defaults(func=self.tasks_manager.update)
        
        # 'MARK' command
        # ====================
        self.mark_task_parser = self.actions_subparser.add_parser(
            "mark", 
            help="Mark a task with a new status.")
        
        self.mark_task_parser.add_argument(
            "id", 
            type=str, 
            help="ID of the task to be marked.")
        self.mark_task_parser.add_argument(
            "new_status", 
            type=str, 
            help="The new status for the task.",
            choices=SUPPORTED_STATUS)
        
        self.mark_task_parser.set_defaults(func=self.tasks_manager.mark)
        
        # 'DELETE' command
        # ====================
        self.del_task_parser = self.actions_subparser.add_parser(
            "delete", 
            help="Deletes a task.")
        
        self.del_task_parser.add_argument(
            "id", 
            type=str, 
            help="ID of the task to be deleted.")
        
        self.del_task_parser.add_argument(
            "-f", 
            "--forced",
            action="store_true",
            help="If not used, the user will be prompted for confirmation.")
        
        self.del_task_parser.set_defaults(func=self.tasks_manager.delete)
        
        # 'LIST' command
        # ====================
        self.list_task_parser = self.actions_subparser.add_parser(
            "list", 
            help="List all tasks.")
        
        self.list_task_parser.add_argument(
            "-s", 
            "--status",
            type=str, 
            help="To list all tasks with a given status.",
            choices=SUPPORTED_STATUS,
            default=None)

        self.list_task_parser.add_argument(
            "-p", 
            "--priority",
            type=str, 
            help="To list all tasks with a given priority.",
            choices=SUPPORTED_PRIORITIES,
            default=None)
        
        self.list_task_parser.set_defaults(func=self.tasks_manager.list)


    def start_parsing(self) -> None:
        """ Parses the arguments passed. """
        args = self.main_parser.parse_args()
        args.func(args)