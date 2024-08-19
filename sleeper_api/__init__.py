# Import the main client class for easy access
from .client import SleeperClient

# Import specific resource classes if needed
from .resources.user import User
from .resources.league import League
from .resources.draft import Draft
from .resources.player import Player

# Import any exceptions you want to expose
from .exceptions import SleeperAPIError, UserNotFoundError

# Define the public API of the package
__all__ = [
    "SleeperClient",
    "User",
    "League",
    "Draft",
    "Player",
    "SleeperAPIError",
    "UserNotFoundError",
]