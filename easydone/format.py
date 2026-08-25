def print_table(tasks: dict[str, dict], ids: list[str]) -> None:
    """ Prints the tasks using 'rich' package. Fallbacks to plain text if rich isn't available. """
    try:
        import rich
        # Use rich
    except ImportError:
        print("Warning: Rich isn't available")
        # Use plain text

        print("====================================")
        print("EasyDone: Task-Tracker")
        print("====================================")
        for id in ids:
            desc = tasks[id]['description']
            prior = tasks[id]['priority']
            stat = tasks[id]['status']
            create = tasks[id].get('created-at', 'unknown')
            update = tasks[id].get('updated-at', 'unknown')
            print(f"ID: {id} \"{desc}\" [{prior}] [{stat}] [{create}], [{update}]")
        print("====================================")