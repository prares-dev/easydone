from argparse import ArgumentParser, Namespace, SUPPRESS
from .logic import TasksManager
from .format import print_table
from . import __version__

SUPPORTED_STATUS = ["not-done", "done", "in-progress"]
SUPPORTED_PRIORITIES = ["low", "normal", "high", "urgent"]

class CLIApp():
    """ A class to manage all the CLIApp features. """
    
    def __init__(self, tasks_from_file: dict[str, dict]) -> None:
        """Initialize the CLIApp attributes"""
        self.tasks_manager = TasksManager(tasks_from_file)
        self.build_parser()
    
    def build_parser(self) -> None:
        """ Create the main parser and sub-commands. """
        self.main_parser = ArgumentParser(
            prog = "EasyDone",
            description = "Task-Tracker. Create, delete, edit, do.",
            epilog = "Thanks for using %(prog)s! :)\nAll feedback is appreciated.",
            allow_abbrev = False # disable auto option abbreviation
        )
        
        # Shows the current version running
        self.main_parser.add_argument(
            '-v',
            '--version',
            help='Display app version.',
            action="version",
            version="%(prog)s " + __version__
        )
        
        # Sub-commands parser
        actions_subparser = self.main_parser.add_subparsers(
            title="actions", 
            help="Supported commands."
            )
        
        # 'NEW' command
        # ====================
        
        # Create parser for 'new' command
        new_task_parser = actions_subparser.add_parser(
            "new", 
            help="Create a new task")
        
        new_task_parser.add_argument(
            "description", 
            type=str, 
            help="Description of the task to be added.")
        
        # optional flag for indicating initial status
        new_task_parser.add_argument(
            "-s",
            "--status", 
            type=str, 
            help="Optional initial status: defaults to 'not-done'.",
            choices=SUPPORTED_STATUS,
            default=SUPPORTED_STATUS[0])
        
        # optional flag for indicating initial priority
        new_task_parser.add_argument(
            "-p",
            "--priority", 
            type=str, 
            help="Optional priority: defaults to 'low'.",
            choices=SUPPORTED_PRIORITIES,
            default=SUPPORTED_PRIORITIES[0])
        
        # assign 'new' method from TasksManager to func attr of the Namespace returned by parser
        new_task_parser.set_defaults(func=self.tasks_manager.new)
        
        # 'UPDATE' command
        # ====================
        update_task_parser = actions_subparser.add_parser(
            "update", 
            help="Update a task.",
            argument_default=SUPPRESS)
        
        update_task_parser.add_argument(
            "id",
            type=str, 
            help="ID of the task to be updated.")
        
        update_task_parser.add_argument(
            "-d",
            "--description", 
            metavar="new-description",
            type=str, 
            help="Update description.")
        
        update_task_parser.add_argument(
            "-p",
            "--priority", 
            metavar="new-priority",
            type=str, 
            help="Update priority.")

        update_task_parser.set_defaults(func=self.tasks_manager.update)
        
        # 'MARK' command
        # ====================
        mark_task_parser = actions_subparser.add_parser(
            "mark", 
            help="Mark a task with a new status.")
        
        mark_task_parser.add_argument(
            "id", 
            type=str, 
            help="ID of the task to be marked.")
        mark_task_parser.add_argument(
            "new_status", 
            type=str, 
            help="The new status for the task.",
            choices=SUPPORTED_STATUS)
        
        mark_task_parser.set_defaults(func=self.tasks_manager.mark)
        
        # 'DELETE' command
        # ====================
        del_task_parser = actions_subparser.add_parser(
            "delete", 
            help="Deletes a task.")
        
        del_task_parser.add_argument(
            "id", 
            type=str, 
            help="ID of the task to be deleted.")
        
        del_task_parser.add_argument(
            "-f", 
            "--forced",
            action="store_true",
            help="If not used, the user will be prompted for confirmation.")
        
        del_task_parser.set_defaults(func=self.tasks_manager.delete)
        
        # 'LIST' command
        # ====================
        list_task_parser = actions_subparser.add_parser(
            "list", 
            help="List all tasks.")
        
        list_task_parser.add_argument(
            "-s", 
            "--status",
            type=str, 
            help="To list all tasks with a given status.",
            choices=SUPPORTED_STATUS,
            default=None)

        list_task_parser.add_argument(
            "-p", 
            "--priority",
            type=str, 
            help="To list all tasks with a given priority.",
            choices=SUPPORTED_PRIORITIES,
            default=None)
    
        list_task_parser.add_argument(
            "--no-dates", 
            help="Not ouput dates.",
            action="store_true")
        
        list_task_parser.set_defaults(func=self.tasks_manager.list)

    def start_parsing(self) -> None:
        """ Parses the arguments passed. """
        args: Namespace
        try:
            args = self.main_parser.parse_args()
        except AttributeError:
            # in case user invokes the program without arguments like:
            # >>> easydone
            self.main_parser.print_help()
            return
        except ValueError as exc:
            self.main_parser.error(str(exc))
            return

        if getattr(args, 'func', None) == self.tasks_manager.update:
            has_update_target = hasattr(args, 'description') or hasattr(args, 'priority')
            if not has_update_target:
                self.main_parser.error("the update command requires at least one field change: --description or --priority")

        elif getattr(args, 'func', None) == self.tasks_manager.list:
            filtered_ids = args.func(args)
            print_table(self.tasks_manager.tasks, filtered_ids, no_dates=args.no_dates)    

        else: args.func(args)