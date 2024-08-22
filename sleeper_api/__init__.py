# Import the main client class for easy access
from .client import SleeperClient

# Import specific resource classes if needed
from .endpoints.user_endpoint import UserEndpoint
# from .resources.league import LeagueEndpoint
# from .resources.draft import DraftEndpoint
# from .resources.player import PlayerEndpoint

# Import any exceptions you want to expose
from .exceptions import SleeperAPIError, UserNotFoundError

# Define the public API of the package
__all__ = [
    "SleeperClient",
    "UserEndpoint",
    # "LeagueEndpoint",
    # "DraftEndpoint",
    # "PlayerEndpoint",
    "SleeperAPIError",
    "UserNotFoundError",
]