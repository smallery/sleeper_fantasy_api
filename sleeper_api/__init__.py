"""
define what is accessible for the sleeper_api
"""
# Import the main client class for easy access
from .client import SleeperClient

# Import specific resource classes if needed
from .endpoints.user_endpoint import UserEndpoint
from .endpoints.league_endpoint import LeagueEndpoint
from .endpoints.draft_endpoint import DraftEndpoint
from .endpoints.player_endpoint import PlayerEndpoint

# Import specific data models
from .models.brackets import BracketModel
from .models.draft import DraftModel
from .models.league import LeagueModel
from .models.matchups import MatchupModel
from .models.picks import PicksModel
from .models.player import PlayerModel
from .models.roster import RosterModel
from .models.traded_picks import TradedDraftPicksModel
from .models.transactions import TransactionsModel
from .models.user import UserModel

# Import any exceptions you want to expose
from .exceptions import SleeperAPIError, UserNotFoundError

# Define the public API of the package
__all__ = [
    "SleeperClient",
    "UserEndpoint",
    "LeagueEndpoint",
    "DraftEndpoint",
    "PlayerEndpoint",
    "BracketModel",
    "DraftModel",
    "LeagueModel",
    "MatchupModel",
    "PicksModel",
    "PlayerModel",
    "RosterModel",
    "TradedDraftPicksModel",
    "TransactionsModel",
    "UserModel",
    "SleeperAPIError",
    "UserNotFoundError",
]

__version__ = "0.1.0"
