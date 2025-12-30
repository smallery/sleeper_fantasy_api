"""
This module provides the `LeagueEndpoint` class for interacting 
with league-related API endpoints of the Sleeper API.

The `LeagueEndpoint` class includes methods for retrieving league details,
rosters, users, matchups, brackets, transactions, and traded picks.
It supports optional conversion of results into model instances.
"""
from typing import Dict, List
from ..models.league import LeagueModel
from ..models.roster import RosterModel
from ..models.matchups import MatchupModel
from ..models.brackets import BracketModel
from ..models.transactions import TransactionsModel
from ..models.traded_picks import TradedPickModel
from ..models.nfl_state import NFLStateModel
from ..models.variance import TeamVarianceModel
from .user_endpoint import UserEndpoint
from ..config import CONVERT_RESULTS
from ..exceptions import SleeperAPIError

class LeagueEndpoint:
    """
    Provides methods for interacting with league-related API endpoints of the Sleeper API.

    Methods:
    --------
    - `get_league(league_id: str) -> LeagueModel`:
        Retrieves a specific league by its ID.

    - `get_rosters(league_id: str, convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves rosters for a given league. 
        Optionally converts results into `RosterModel` instances.

    - `get_users(league_id: str, convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves users in a given league. 
        Optionally converts results into user model objects.

    - `get_matchups(league_id: str, week: int, 
                    convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves matchups for a given league and week. 
        Optionally converts results into `MatchupModel` instances.

    - `get_winners_bracket(league_id: str, 
                            convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves the winner's bracket for a given league. 
        Optionally converts results into `BracketModel` instances.

    - `get_losers_bracket(league_id: str, 
                          convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves the loser's bracket for a given league. 
        Optionally converts results into `BracketModel` instances.

    - `get_transactions(league_id: str, week: int, 
                        convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves transactions for a given league, filtered by week. 
        Optionally converts results into `TransactionsModel` instances.

    - `get_traded_picks(league_id: str, 
                        convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves traded picks for a given league. 

    Attributes:
    -----------
    - `client`: An instance of the API client used to make requests to the Sleeper API.

    Exception Handling:
    -------------------
    - `SleeperAPIError`: Raised for API errors and invalid responses.
    """
    def __init__(self, client):
        self.client = client

    def get_league_by_id(self, league_id: str) -> LeagueModel:
        """
        Retrieve a specific league by its ID.
        """
        endpoint = f"league/{league_id}"
        league_data = self.client.get(endpoint)
        if league_data is None:
            raise SleeperAPIError("League not found")
        return LeagueModel.from_json(league_data)

    def get_rosters(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the rosters for a given league.
        """
        endpoint = f"league/{league_id}/rosters"
        rosters_json = self.client.get(endpoint)
        if not convert_results:
            return rosters_json

        return [RosterModel.from_dict(roster_data) for roster_data in rosters_json]

    def get_users(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the users in a given league.
        Returns a list of users. 
            - If convert_results = False, this will be the raw JSON.
            - If convert_results = True, then this will be a list of user model objects
        """
        endpoint = f"league/{league_id}/users"
        users_json = self.client.get(endpoint)

        if not convert_results:
            return users_json

        # note: the username will be missing from these user records, this can be retrieved
        user_endpoint = UserEndpoint(self.client)
        return [user_endpoint.get_user(user.get("user_id")) for user in users_json]

    def get_matchups(
            self, league_id: str, week: int,
            convert_results = CONVERT_RESULTS
            ) -> List[Dict]:
        """
        Retrieve the matchups for a given league and week.
        """

        # TO DO:   combine matchups into a single model
                #  so you can find both teams in the same matchup object
        endpoint = f"league/{league_id}/matchups/{week}"
        matchup_json = self.client.get(endpoint)

        if not convert_results:
            return matchup_json

        return [MatchupModel.from_dict(matchup_data) for matchup_data in matchup_json]

    def get_winners_bracket(
            self, league_id: str, convert_results = CONVERT_RESULTS
            ) -> List[Dict]:
        """
        Retrieve the winner's bracket for a given league.
        """
        endpoint = f"league/{league_id}/winners_bracket"
        bracket_json = self.client.get(endpoint)

        if not convert_results:
            return bracket_json

        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    def get_losers_bracket(
            self, league_id: str, convert_results = CONVERT_RESULTS
            ) -> List[Dict]:
        """
        Retrieve the loser's bracket for a given league.
        """
        endpoint = f"league/{league_id}/losers_bracket"
        bracket_json = self.client.get(endpoint)

        if not convert_results:
            return bracket_json

        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    def get_transactions(
            self, league_id: str, week: int, convert_results = CONVERT_RESULTS
            ) -> List[Dict]:
        """
        Retrieve transactions for a given league. Filter by week.
        """
        endpoint = f"league/{league_id}/transactions/{week}"
        transactions_json = self.client.get(endpoint)

        if not convert_results:
            return transactions_json

        return [TransactionsModel.from_dict(transaction_data) for transaction_data in transactions_json]

    def get_traded_picks(
            self, league_id: str, convert_results = CONVERT_RESULTS
            ) -> List[Dict]:
        """
        Retrieve traded picks for a given league.
        """
        endpoint = f"league/{league_id}/traded_picks"
        traded_picks_json = self.client.get(endpoint)

        if not convert_results:
            return traded_picks_json

        return [TradedPickModel.from_dict(traded_pick) for traded_pick in traded_picks_json]

    def get_nfl_state(self, convert_results = CONVERT_RESULTS):
        """
        Get the current NFL state (season, week, etc.).

        Returns:
            NFLStateModel or dict with current season information.
        """
        endpoint = "state/nfl"
        state_data = self.client.get(endpoint)

        if not convert_results:
            return state_data

        return NFLStateModel.from_dict(state_data)

    def calculate_team_variances(
        self,
        league_id: str,
        through_week: int,
        current_week_projections: Dict[int, float] = None
    ) -> List[TeamVarianceModel]:
        """
        Calculate historical scoring variance for all teams in a league.

        Fetches all weekly scores through the specified week and calculates
        variance metrics (mean, stddev, floor, ceiling) for each team.

        Args:
            league_id: The league ID.
            through_week: The week to calculate variance through.
            current_week_projections: Optional dict of roster_id -> projected points.

        Returns:
            List of TeamVarianceModel objects for each team in the league.
        """
        current_week_projections = current_week_projections or {}

        # Get rosters and users for team info
        rosters = self.get_rosters(league_id, convert_results=True)
        users = self.get_users(league_id, convert_results=True)

        # Build roster to user mapping
        user_by_id = {user.user_id: user for user in users}
        roster_map = {}
        for roster in rosters:
            user = user_by_id.get(roster.owner_id)
            roster_map[roster.roster_id] = {
                'display_name': user.display_name if user else f"Team {roster.roster_id}",
                'team_name': (user.metadata.get('team_name') if user and hasattr(user, 'metadata')
                             else user.display_name if user else f"Team {roster.roster_id}")
            }

        # Build weekly scores for each roster
        roster_scores: Dict[int, List[float]] = {}
        for roster in rosters:
            roster_scores[roster.roster_id] = []

        # Fetch matchups for each week
        for week in range(1, through_week + 1):
            try:
                matchups = self.get_matchups(league_id, week, convert_results=True)
                for matchup in matchups:
                    if matchup.roster_id in roster_scores and matchup.points > 0:
                        roster_scores[matchup.roster_id].append(matchup.points)
            except SleeperAPIError:
                # Skip weeks that don't exist or failed to fetch
                continue

        # Calculate variance for each team
        variances: List[TeamVarianceModel] = []
        for roster in rosters:
            team_info = roster_map.get(roster.roster_id, {})
            variance = TeamVarianceModel.from_weekly_scores(
                roster_id=roster.roster_id,
                display_name=team_info.get('display_name', f"Team {roster.roster_id}"),
                team_name=team_info.get('team_name', f"Team {roster.roster_id}"),
                weekly_scores=roster_scores.get(roster.roster_id, []),
                projection=current_week_projections.get(roster.roster_id, 0.0),
            )
            variances.append(variance)

        return variances
