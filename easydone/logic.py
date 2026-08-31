from random import randint
from datetime import datetime
from typing import Optional, Literal

SUPPORTED_STATUS = ["not-done", "done", "in-progress"]
SUPPORTED_PRIORITIES = ["low", "normal", "high", "urgent"]

class TasksManager():
    """ A class to manage all tasks logic. """
    def __init__(self, tasks_from_file:dict[str, dict]):
        self.tasks = tasks_from_file # internal dict for tracking tasks
        self.ID_SIZE = 3 # number of digits to generate for an ID
    
    def new(self, description: str, *, 
            status: str = 'not-done', 
            priority: str = 'low'
            ) -> Literal[True]:
        """ Create a new task. """
        if status not in SUPPORTED_STATUS:
            raise ValueError(f"Attempting to create new task with invalid status: {status}")
        elif priority not in SUPPORTED_PRIORITIES:
            raise ValueError(f"Attempting to create new task with invalid priority: {priority}")
        
        id = self._task_id()
        self.tasks[id] = {
            "description": description, 
            "status": status,
            "priority": priority,
            "created-at": str(datetime.now()).split(" ")[0],
            "updated-at": None
            }
        return True

    def update( self, id: str, *, 
                new_descr: Optional[str], 
                new_prior: Optional[str]
                ) -> bool:
        """ Updates a task. """
        if id not in self.tasks:
            raise KeyError("Nonexistent task ({id})")
        elif new_prior not in SUPPORTED_PRIORITIES:
            raise ValueError(f"Attempting to update task: {id} with invalid priority: {new_prior}")
        
        task = self.tasks[id]
        if new_descr and new_descr == task['description']:
            raise ValueError("New description must be different from the current description.")
        elif new_prior and new_prior == task['priority']:
            raise ValueError("New priority must be different from the current priority.")
        
        updated = False
        if new_descr:
            task['description'] = new_descr
            updated = True

        if new_prior:
            task['priority'] = new_prior
            updated = True

        if updated:
            task['updated-at'] = str(datetime.now()).split(" ")[0]
        
        return updated
    
    def mark(self, id: str, new_status: str) -> bool:
        """Marking task as done, not done or in progress"""
        if id not in self.tasks:
            raise KeyError("Nonexistent task ({id})")
        elif new_status not in SUPPORTED_STATUS:
            raise ValueError(f"Attempting to update task: {id} with invalid status: {new_status}")

        self.tasks[id]["status"] = new_status
        self.tasks[id]["updated-at"] = str(datetime.now()).split(" ")[0]
        return True
    
    def delete(self, *ids: str) -> list[str]:
        """Deletes the given ids and returns the ones actually removed."""
        for id in ids:
            if id not in self.tasks:
                raise KeyError(f"Nonexistent task ({id})")
        removed = []
        for id in ids:
            self.tasks.pop(id)
            removed.append(id)
        return removed
            
    def list(   self, *, 
                status: Optional[str], 
                priority: Optional[str]
                ) -> list[str]:
        """ Returns a filtered list of ids according to status and priority. """
        if status not in SUPPORTED_STATUS or priority not in SUPPORTED_PRIORITIES:
            raise ValueError("Using invalid filters.")
        
        ids = []
        for key, value in self.tasks.items():
            # check if task passes filters
            if (status is None or value['status'] == status) and (priority is None or value['priority'] == priority):
                ids.append(key)
        
        return ids
    
    def _task_id(self) -> str:
        """ Returns a random id, formed by digits, the number of digits is determined by self.ID_SIZE"""
        id = None
        # keeps generating until gets an id that's not already present.
        while id is None or id in self.tasks:
            id = ""
            for _ in range(self.ID_SIZE):
                id += str(randint(0, 9))
        return id