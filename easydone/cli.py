from argparse import ArgumentParser, Namespace, SUPPRESS
from .logic import TasksManager
from .format import print_table
from . import __version__

SUPPORTED_STATUS = ["not-done", "done", "in-progress"]
SUPPORTED_PRIORITIES = ["low", "normal", "high", "urgent"]

class Parser():
    """ A class to manage all the argument parser and command features. """
    
    def __init__(self, manager: TasksManager) -> None:
        """Initialize the CLIApp attributes"""
        if not isinstance (manager, TasksManager):
            raise TypeError()
            
        self.tasks_manager = manager
        self.build_parser()
    
    def build_parser(self) -> None:
        """ Create the main parser and sub-commands. """
        description = "Simple and powerfull task tracker. Helps you manage your to-do list directly from the terminal."
        self.main_parser = ArgumentParser(
            prog = "EasyDone", description = description, allow_abbrev = False,
            epilog = "Thanks for using %(prog)s! :)\nAll feedback is appreciated.", )
        
        # Show the current version running.
        self.main_parser.add_argument(
            '-v', '--version', help='Display app version.', action="version",
            version="%(prog)s " + __version__)
        
        # Sub-commands parser
        sub_pars = self.main_parser.add_subparsers(title="actions")
        
        # 'NEW' command
        # ====================
        
        # Create parser for 'new' command
        new_pars = sub_pars.add_parser("new", help="Create a new task")
        new_pars.add_argument(
            "description", type=str, 
            help="Description of the task to be added.")
        
        # optional flag for indicating initial status
        new_pars.add_argument(
            "-s", "--status", type=str, 
            help="Optional initial status: defaults to 'not-done'.",
            choices=SUPPORTED_STATUS, default=SUPPORTED_STATUS[0])
        
        # optional flag for indicating initial priority
        new_pars.add_argument(
            "-p", "--priority", type=str, 
            help="Optional priority: defaults to 'low'.",
            choices=SUPPORTED_PRIORITIES, default=SUPPORTED_PRIORITIES[0])
        
        # assign 'new' method from TasksManager to func attr of the Namespace returned by parser
        new_pars.set_defaults(func=self.tasks_manager.new)
        
        # 'UPDATE' command
        # ====================
        update_pars = sub_pars.add_parser("update", help="Update a task.", argument_default=SUPPRESS)
        
        update_pars.add_argument(
            "id", type=str, 
            help="ID of the task to be updated.")
        
        update_pars.add_argument(
            "-d", "--description", metavar="new-description", type=str, 
            help="Update description.")
        
        update_pars.add_argument(
            "-p", "--priority", metavar="new-priority",
            type=str, help="Update priority.")

        update_pars.set_defaults(func=self.tasks_manager.update)
        
        # 'MARK' command
        # ====================
        mark_pars = sub_pars.add_parser("mark", help="Mark a task with a new status.")
        
        mark_pars.add_argument(
            "id", type=str, 
            help="ID of the task to be marked.")
        
        mark_pars.add_argument(
            "new_status", type=str, 
            help="The new status for the task.",
            choices=SUPPORTED_STATUS)
        
        mark_pars.set_defaults(func=self.tasks_manager.mark)
        
        # 'DELETE' command
        # ====================
        del_pars = sub_pars.add_parser("delete", help="Deletes a task.")
        
        del_pars.add_argument(
            "id", type=str, 
            help="ID of the task to be deleted.")
        
        del_pars.add_argument(
            "-f", "--forced", action="store_true",
            help="If not used, the user will be prompted for confirmation.")
        
        del_pars.set_defaults(func=self.tasks_manager.delete)
        
        # 'LIST' command
        # ====================
        list_pars = sub_pars.add_parser("list", help="List all tasks.")
        
        list_pars.add_argument(
            "-s", "--status", type=str, 
            help="To list all tasks with a given status.",
            choices=SUPPORTED_STATUS, default=None)

        list_pars.add_argument(
            "-p", "--priority", type=str, 
            help="To list all tasks with a given priority.",
            choices=SUPPORTED_PRIORITIES, default=None)
    
        list_pars.add_argument(
            "--no-dates", action="store_true",
            help="Not ouput dates.",)
        
        list_pars.set_defaults(func=self.tasks_manager.list)

    def start_parsing(self) -> None:
        """ Parses the arguments passed. """
        args: Namespace
        try:
            args = self.main_parser.parse_args()
        except ValueError as exc:
            self.main_parser.error(str(exc))
            return

        if getattr(args, 'func', None) == self.tasks_manager.list:
            filtered_ids = args.func(args)
            print_table(self.tasks_manager.tasks, filtered_ids, no_dates=args.no_dates) 
            return
    
        if getattr(args, 'func', None) == self.tasks_manager.update:
            has_update_target = hasattr(args, 'description') or hasattr(args, 'priority')
            if not has_update_target:
                self.main_parser.error("the update command requires at least one field change: --description or --priority")

        try:
            args.func(args)
        except AttributeError:
            # in case user invokes the program without arguments like:
            # >>> easydone
            self.main_parser.print_help()
        except (ValueError, KeyError) as exc:
            self.main_parser.error(str(exc))