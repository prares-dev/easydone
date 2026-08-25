from importlib.metadata import version, PackageNotFoundError

try:
    # use the distribution name from pyproject 'project.name' (make sure they match)
    __version__ = version("easydone-task-tracker")
except PackageNotFoundError:
    # Package isn't installed (dev environment). Optional fallback:
    __version__ = "0.0.0+dev"