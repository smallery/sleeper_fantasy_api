"""
define what is accessible for the sleeper_api
"""
# Import the main client class for easy access
from .client import SleeperClient
from .endpoints.draft_endpoint import DraftEndpoint
from .endpoints.league_endpoint import LeagueEndpoint
from .endpoints.nfl_endpoint import NFLEndpoint
from .endpoints.player_endpoint import PlayerEndpoint
from .endpoints.projections_endpoint import ProjectionsEndpoint

# Import specific resource classes if needed
from .endpoints.user_endpoint import UserEndpoint

# Import any exceptions you want to expose
from .exceptions import LeagueNotFoundError, RateLimitError, SleeperAPIError, UserNotFoundError

# Import specific data models
from .models.brackets import BracketModel
from .models.draft import DraftModel
from .models.league import LeagueModel
from .models.matchups import MatchupModel
from .models.picks import PicksModel
from .models.player import PlayerModel
from .models.roster import RosterModel
from .models.schedule import NFLScheduleModel, ScheduleGameModel
from .models.team_depth_chart import TeamDepthChartModel
from .models.traded_picks import TradedPickModel
from .models.transactions import TransactionsModel
from .models.user import UserModel

# Define the public API of the package
__all__ = [
    "SleeperClient",
    "UserEndpoint",
    "LeagueEndpoint",
    "DraftEndpoint",
    "PlayerEndpoint",
    "ProjectionsEndpoint",
    "NFLEndpoint",
    "BracketModel",
    "DraftModel",
    "LeagueModel",
    "MatchupModel",
    "PicksModel",
    "PlayerModel",
    "RosterModel",
    "TradedPickModel",
    "TransactionsModel",
    "UserModel",
    "TeamDepthChartModel",
    "NFLScheduleModel",
    "ScheduleGameModel",
    "SleeperAPIError",
    "UserNotFoundError",
    "LeagueNotFoundError",
    "RateLimitError",
]

__version__ = "0.5.0"
