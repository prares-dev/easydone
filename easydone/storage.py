import json
from pathlib import Path

class JSONHandler():
    def __init__(self, json_file: str = "data/tasks.json"):
        """ Initialize attributes. """
        self.json_file = json_file
    
    def load(self) -> dict[str, dict]:
        """ Loads content from a json file. """
        try:
            with open(self.json_file, 'r') as file:
                tasks = json.load(file)
                return tasks
        except FileNotFoundError:
            print(f'{self.json_file} doesn\'t exists in the current directory.')
            print("Starting with empty task list...")
            return {}
    
    def save(self, tasks: dict[str, dict]):
        """ Saves a tasks dictionary to the registered json_file. If doesn't exist it creates it. """
        # create parent directory if needed
        Path(self.json_file).parent.mkdir(parents=True, exist_ok=True)
        # write to file and create if needed
        with open(self.json_file, 'w') as file:
            json.dump(tasks, file, indent=4)