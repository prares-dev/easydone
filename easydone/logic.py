from argparse import Namespace
from random import randint
from datetime import datetime

class TasksManager():
    """ A class to manage all tasks logic. """
    def __init__(self, tasks_from_file:dict[str, dict]):
        self.tasks = tasks_from_file # internal dict for tracking tasks
        self.ID_SIZE = 3 # number of digits to generate for an ID
    
    def new(self, args: Namespace):
        """ Create a new task. """
        self.tasks[self.task_id()] = {
            "description": args.description, 
            "status": args.status,
            "priority": args.priority,
            "created-at": str(datetime.now()).split(" ")[0],
            "updated-at": None
            }

    def update(self, args: Namespace):
        """ Updates a task. """
        if args.id not in self.tasks:
            raise KeyError("Unexistent task")

        task = self.tasks[args.id]
        if hasattr(args, 'description') and args.description == task['description']:
            raise ValueError("New description must be different from the current description.")

        if hasattr(args, 'priority') and args.priority == task['priority']:
            raise ValueError("New priority must be different from the current priority.")

        if hasattr(args, 'description'):
            task['description'] = args.description

        if hasattr(args, 'priority'):
            task['priority'] = args.priority

        task['updated-at'] = str(datetime.now()).split(" ")[0]
    
    def mark(self, args: Namespace):
        """Marking task as done, not done or in progress"""
        if (id := args.id) not in self.tasks:
            raise KeyError("Unexistent task")

        self.tasks[args.id]["status"] = args.new_status
        self.tasks[args.id]["updated-at"] = str(datetime.now()).split(" ")[0]
    
    def delete(self, *ids: str):
        """Deletes the given ids and returns the ones actually removed."""
        for id in ids:
            if id not in self.tasks:
                raise KeyError(f"Unexistent task ({id})")
        removed = []
        for id in ids:
            self.tasks.pop(id)
            removed.append(id)
        return removed
            
    def list(self, args: Namespace) -> list[str]:
        """ Shows all tasks. Filtered according to args.status and args.priority. """
        ids = []
        
        s_filt = args.status
        p_filt = args.priority
        for key, value in self.tasks.items():
            # check if task passes filters
            if (s_filt is None or value['status'] == s_filt) and (p_filt is None or value['priority'] == p_filt):
                ids.append(key)
        
        return ids
    
    def task_id(self) -> str:
        """ Returns a random id, formed by digits, the number of digits is determined by self.ID_SIZE"""
        id = None
        # keeps generating until gets an id that's not already present.
        while id is None or id in self.tasks:
            id = ""
            for _ in range(self.ID_SIZE):
                id += str(randint(0, 9))
        return id