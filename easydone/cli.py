from argparse import ArgumentParser, Namespace, SUPPRESS
from .logic import TasksManager, SUPPORTED_PRIORITIES, SUPPORTED_STATUS
from .format import print_table, confirm_deletion
from . import __version__

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
        new_pars.set_defaults(func=self._handle_new)
        
        # 'UPDATE' command
        # ====================
        update_pars = sub_pars.add_parser("update", help="Update a task.")
        
        update_pars.add_argument(
            "id", type=str, 
            help="ID of the task to be updated.")
        
        update_pars.add_argument(
            "-d", "--description", metavar="new-description", type=str, 
            help="Update description.")
        
        update_pars.add_argument(
            "-p", "--priority", metavar="new-priority",
            type=str, help="Update priority.", 
            choices=SUPPORTED_PRIORITIES)

        update_pars.set_defaults(func=self._handle_update)
        
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
        
        mark_pars.set_defaults(func=self._handle_mark)
        
        # 'DELETE' command
        # ====================
        del_pars = sub_pars.add_parser("delete", help="Deletes a task.")
        
        del_pars.add_argument(
            "ids", type=str, nargs='+', metavar='id',
            help="IDs of the tasks to be deleted.")
        
        del_pars.add_argument(
            "-f", "--forced", action="store_true",
            help="If not used, the user will be prompted for confirmation.")
        
        del_pars.set_defaults(func=self._handle_delete)
        
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
        
        list_pars.set_defaults(func=self._handle_list)

    def start_parsing(self) -> bool:
        """ Parses the arguments passed. Returns true if some command mutated state of any task. """
        args: Namespace
        try:
            args = self.main_parser.parse_args()
        except ValueError as exc:
            self.main_parser.error(str(exc))
            return False
        
        if not hasattr(args, 'func'):
            # in case user invokes the program without arguments like:
            # >>> easydone
            self.main_parser.print_help()
            return False
        else:
            try:
                return args.func(args)
            except (KeyError, ValueError) as exc:
                self.main_parser.error(str(exc))

    def _handle_delete(self, args: Namespace) -> bool:
        unique_ids = list(dict.fromkeys(args.ids))  # dedupe, preserve order

        # validate before prompting — never ask the user to confirm a phantom task
        for id in unique_ids:
            if id not in self.tasks_manager.tasks:
                raise KeyError(f"Nonexistent task ({id})")

        to_remove = []
        if args.forced: to_remove = unique_ids
        else:
            for id in unique_ids: 
                try:
                    if confirm_deletion(id, self.tasks_manager.tasks[id]['description']):
                        to_remove.append(id)
                except KeyboardInterrupt:
                        return False
        removed = self.tasks_manager.delete(to_remove)
        
        return bool(removed)

    def _handle_list(self, args: Namespace) -> bool:
        filtered_ids = self.tasks_manager.list(
            status=args.status, priority=args.priority
            )
        print_table(
            self.tasks_manager.tasks, 
            filtered_ids, no_dates=args.no_dates)
        return False

    def _handle_update(self, args: Namespace) -> bool:
        has_update_target = args.description or args.priority
        if not has_update_target:
            self.main_parser.error("the update command requires at least one field change: --description or --priority")
        return self.tasks_manager.update(
                args.id, 
                new_descr=args.description, 
                new_prior=args.priority
                )

    def _handle_new(self, args: Namespace) -> bool:
        return self.tasks_manager.new(
            description=args.description,
            status=args.status,
            priority=args.priority
        )

    def _handle_mark(self, args: Namespace) -> bool:
        return self.tasks_manager.mark(
            id=args.id, new_status=args.new_status
        )