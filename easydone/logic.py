from re import fullmatch
from random import randint
from datetime import datetime, timedelta
from typing import Optional, Literal, Union

SUPPORTED_STATUS = ["not-done", "in-progress", "done",]
SUPPORTED_PRIORITIES = ["low", "normal", "high", "urgent"]

STATUS_ORDER = {status: int(i) 
                for i, status in enumerate(SUPPORTED_STATUS)}

PRIORITY_ORDER = {  prior: int(i) 
                    for i, prior in enumerate(SUPPORTED_PRIORITIES)}


class TasksManager():
    """ A class to manage all tasks logic. """
    def __init__(self, tasks_from_file: dict[str, dict]):
        self.tasks = tasks_from_file
        self.ID_SIZE = 3

    def new(self, description: str, *,
            status: str = 'not-done',
            priority: str = 'low',
            due_date: Optional[str] = None
            ) -> Literal[True]:
        """ Create a new task. """
        if status not in SUPPORTED_STATUS:
            raise ValueError(f"Attempting to create new task with invalid status: {status}")
        elif priority not in SUPPORTED_PRIORITIES:
            raise ValueError(f"Attempting to create new task with invalid priority: {priority}")
        elif due_date and not self._valid_date(due_date):
            raise ValueError(f"Invalid due date ({due_date}), please use format YYYY-MM-DD")

        id = self._task_id()
        self.tasks[id] = {
            "description": description,
            "status": status,
            "priority": priority,
            "due": due_date,
            "created-at": str(datetime.now()).split(" ")[0],
            "updated-at": None
        }
        return True

    def update( self, id: str, *,
                new_descr: Optional[str] = None,
                new_prior: Optional[str] = None,
                new_due: Optional[str] = None,
                ) -> bool:
        """ Updates a task. """
        if id not in self.tasks:
            raise KeyError(f"Nonexistent task ({id})")
        else: 
            task = self.tasks[id]
        
        if new_prior is not None:
            if new_prior not in SUPPORTED_PRIORITIES:
                raise ValueError(f"Attempting to update task: {id} with invalid priority: {new_prior}")
            elif new_prior == task['priority']:
                raise ValueError("New priority must be different from the current one.")
            
        if new_due is not None:
            if not self._valid_date(new_due):
                raise ValueError(f"Attempting to update task: {id} with invalid due date {new_due}, please use format YYYY-MM-DD")
            elif hasattr(task, 'due') and new_due == task['due']:
                raise ValueError("New due date must be different from the current one.")
            
        if new_descr is not None and new_descr == task['description']:
            raise ValueError("New description must be different from the current on.")

        updated = False
        if new_descr is not None:
            task['description'] = new_descr
            updated = True
            
        if new_prior is not None:
            task['priority'] = new_prior
            updated = True

        if new_due:
            task['due'] = new_due
            updated = True

        if updated:
            task['updated-at'] = str(datetime.now()).split(" ")[0]

        return updated

    def mark(self, id: str, new_status: str) -> bool:
        """Marking task as done, not done or in progress"""
        if id not in self.tasks:
            raise KeyError(f"Nonexistent task ({id})")
        if new_status not in SUPPORTED_STATUS:
            raise ValueError(f"Attempting to update task: {id} with invalid status: {new_status}")

        self.tasks[id]["status"] = new_status
        self.tasks[id]["updated-at"] = str(datetime.now()).split(" ")[0]
        return True

    def delete(self, ids: list[str]) -> list[str]:
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
                filt_status: Optional[str] = None,
                filt_priority: Optional[str] = None,
                filt_overdue: bool = False,
                sort_by: Optional[str] = None,
                reverse: bool = False
                ) -> list[str]:
        """ Returns a filtered list of ids according to status and priority. """
        
        # validate filters
        if filt_status is not None and filt_status not in SUPPORTED_STATUS:
            raise ValueError(f"Invalid status filter: {filt_status}")
        if filt_priority is not None and filt_priority not in SUPPORTED_PRIORITIES:
            raise ValueError(f"Invalid priority filter: {filt_priority}")

        if not self.tasks:
            return []
        
        filtered = []
        for key, value in self.tasks.items():
            if (filt_status is None or value['status'] == filt_status) and (filt_priority is None or value['priority'] == filt_priority):
                due = value.get('due', '9999')
                due = due if due else '9999'
                if not filt_overdue or is_overdue(value):
                    filtered.append(key)
                
        
        def key_func(task_id: str) -> int | str:
            if sort_by == "status":
                return STATUS_ORDER[self.tasks[task_id]['status']]
        
            elif sort_by == "priority":
                return PRIORITY_ORDER[self.tasks[task_id]['priority']]
        
            elif sort_by == "created":
                return self.tasks[task_id].get('created-at', '0')

            elif sort_by == "updated":
                updated = self.tasks[task_id].get('updated-at')
                return updated if updated is not None else '9000-01-01'
            
            else:
                raise ValueError(f"Invalid sort field ({sort_by})")
        
        if sort_by is not None:
            filtered.sort(key=key_func, reverse=reverse)
            
        return filtered
    
    def search(self, query: list[str]) -> list[str]:
        """ Returns a list of ids whose description contains the given term. """
        if not self.tasks:
            return []
        
        matched = []
        for key, value in self.tasks.items():
            if all(term.lower() in value['description'].lower() for term in query):
                matched.append(key)
        
        return matched
    
    def _task_id(self) -> str:
        """ Returns a random id, formed by digits, the number of digits is determined by self.ID_SIZE"""
        id = None
        while id is None or id in self.tasks:
            id = ""
            for _ in range(self.ID_SIZE):
                id += str(randint(0, 9))
        return id
    
    def _valid_date(self, date_str: str) -> bool:
        """ Validates a given str representing a date in the format YYYY-MM-DD"""
        pattern = r'\d{4}-\d{2}-\d{2}'
        return bool(fullmatch(pattern, date_str))

def is_overdue(task: dict) -> bool:
    """ Returns True | False whether the given task is overdue or not. """
    if not isinstance(task, dict):
        raise TypeError()
    
    time = time_to_due(task)
    return time is not None and time.total_seconds() < 0

def time_to_due(task: dict) -> Optional[timedelta]:
    """ Receives a task id and return a boolean indicating if it is overdue or not. """
    if not isinstance(task, dict):
        raise TypeError()
    
    due = task.get('due')
    if due is None:
        return
    
    # convert str to datetime object
    year, month, day = due.split('-')
    due_date = datetime(int(year), int(month), int(day))
    
    return due_date - datetime.now()