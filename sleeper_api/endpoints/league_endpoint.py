"""
This module provides the `LeagueEndpoint` class for interacting
with league-related API endpoints of the Sleeper API.

The `LeagueEndpoint` class includes methods for retrieving league details,
rosters, users, matchups, brackets, transactions, and traded picks.
It supports optional conversion of results into model instances.
"""
from typing import Any, Dict, List, Literal, Optional, Union, cast, overload

from ..exceptions import LeagueNotFoundError
from ..models.brackets import BracketModel
from ..models.league import LeagueModel
from ..models.matchups import MatchupModel
from ..models.nfl_state import NFLStateModel
from ..models.roster import RosterModel
from ..models.traded_picks import TradedPickModel
from ..models.transactions import TransactionsModel
from ..models.user import UserModel
from .user_endpoint import UserEndpoint


class LeagueEndpoint:
    """
    Provides methods for interacting with league-related API endpoints of the Sleeper API.

    Methods:
    --------
    - `get_rosters(league_id: str, convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves rosters for a given league.
        Optionally converts results into `RosterModel` instances.

    - `get_users(league_id: str, convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves users in a given league.
        Optionally converts results into user model objects.

    - `get_matchups(league_id: str, week: int,
                    convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves matchups for a given league and week.
        Optionally converts results into `MatchupModel` instances.

    - `get_winners_bracket(league_id: str,
                            convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves the winner's bracket for a given league.
        Optionally converts results into `BracketModel` instances.

    - `get_losers_bracket(league_id: str,
                          convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves the loser's bracket for a given league.
        Optionally converts results into `BracketModel` instances.

    - `get_transactions(league_id: str, week: int,
                        convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves transactions for a given league, filtered by week.
        Optionally converts results into `TransactionsModel` instances.

    - `get_traded_picks(league_id: str,
                        convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves traded picks for a given league.

    Every method above defaults ``convert_results`` to the owning
    `SleeperClient`'s `convert_results` setting when the argument is omitted
    (``None``) -- see issue #24. Pass it explicitly to override that default
    for a single call.

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

        A caller asked about a specific, named league_id -- a 404 means that
        league does not exist, so this raises LeagueNotFoundError rather
        than returning None (see issue #17). Contrast with e.g.
        get_matchups(), where a missing result for a given week is a normal,
        expected outcome and stays None/empty.

        :raises LeagueNotFoundError: if the given league_id does not exist.
        """
        endpoint = f"league/{league_id}"
        league_data = self.client.get(endpoint)
        if league_data is None:
            raise LeagueNotFoundError(league_id)
        return LeagueModel.from_json(league_data)

    # --- get_rosters -------------------------------------------------------
    # The @overload trio below (see issue #24/#19) gives a caller passing a
    # literal True/False the precise return type, and falls back to the
    # Union when convert_results is omitted (the actual return type depends
    # on the client's configured default, which is not known statically) or
    # passed as a plain `bool` variable.
    @overload
    def get_rosters(self, league_id: str, convert_results: Literal[True]) -> List[RosterModel]: ...
    @overload
    def get_rosters(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_rosters(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[RosterModel]]: ...

    def get_rosters(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[RosterModel]]:
        """
        Retrieve the rosters for a given league.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/rosters"
        rosters_json = self.client.get(endpoint)
        if not convert_results:
            return rosters_json

        return [RosterModel.from_dict(roster_data) for roster_data in rosters_json]

    @overload
    def get_users(self, league_id: str, convert_results: Literal[True]) -> List[UserModel]: ...
    @overload
    def get_users(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_users(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[UserModel]]: ...

    def get_users(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[UserModel]]:
        """
        Retrieve the users in a given league.
        Returns a list of users.
            - If convert_results = False, this will be the raw JSON.
            - If convert_results = True, then this will be a list of user model objects
        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/users"
        users_json = self.client.get(endpoint)

        if not convert_results:
            return users_json

        # note: the username will be missing from these user records, this can be retrieved
        user_endpoint = UserEndpoint(self.client)
        # get_user() is called with convert_results=True explicitly, so this
        # is always a UserModel here despite get_user()'s wider Union return.
        return [cast(UserModel, user_endpoint.get_user(user.get("user_id"), convert_results=True)) for user in users_json]

    def get_complete_league_data(self, league_id: str):
        """
        Fetch league info, rosters, and users in one convenient call.

        This is a convenience method that combines three separate API calls:
        - get_league_by_id() for league details
        - get_rosters() for all rosters
        - get_users() for all users

        Returns:
            Dict with keys:
                - league: LeagueModel instance
                - rosters: List of RosterModel instances
                - users: List of UserModel instances
                - roster_to_user: Dict mapping roster_id -> user_id for quick lookups

        Example:
            >>> league_endpoint = LeagueEndpoint(client)
            >>> data = league_endpoint.get_complete_league_data('123456789')
            >>> print(f"League: {data['league'].name}")
            >>> print(f"Teams: {len(data['rosters'])}")
            >>> # Find owner of roster 1
            >>> owner_id = data['roster_to_user'][1]
            >>> owner = next(u for u in data['users'] if u.user_id == owner_id)
        """
        # Fetch all data. convert_results=True is passed explicitly, so the
        # @overload on get_rosters()/get_users() already narrows these to
        # List[RosterModel]/List[UserModel] -- no cast needed.
        league = self.get_league_by_id(league_id)
        rosters = self.get_rosters(league_id, convert_results=True)
        users = self.get_users(league_id, convert_results=True)

        # Build convenience mapping
        roster_to_user: Dict[Any, Any] = {}
        for roster in rosters:
            roster_to_user[roster.roster_id] = roster.owner_id

        return {
            'league': league,
            'rosters': rosters,
            'users': users,
            'roster_to_user': roster_to_user
        }

    @overload
    def get_matchups(self, league_id: str, week: int, convert_results: Literal[True]) -> List[MatchupModel]: ...
    @overload
    def get_matchups(self, league_id: str, week: int, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_matchups(
        self, league_id: str, week: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[MatchupModel]]: ...

    def get_matchups(
        self, league_id: str, week: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[MatchupModel]]:
        """
        Retrieve the matchups for a given league and week.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results

        # TO DO:   combine matchups into a single model
                #  so you can find both teams in the same matchup object
        endpoint = f"league/{league_id}/matchups/{week}"
        matchup_json = self.client.get(endpoint)

        if not convert_results:
            return matchup_json

        return [MatchupModel.from_dict(matchup_data) for matchup_data in matchup_json]

    @overload
    def get_winners_bracket(self, league_id: str, convert_results: Literal[True]) -> List[BracketModel]: ...
    @overload
    def get_winners_bracket(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_winners_bracket(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[BracketModel]]: ...

    def get_winners_bracket(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[BracketModel]]:
        """
        Retrieve the winner's bracket for a given league.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/winners_bracket"
        bracket_json = self.client.get(endpoint)

        if not convert_results:
            return bracket_json

        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    @overload
    def get_losers_bracket(self, league_id: str, convert_results: Literal[True]) -> List[BracketModel]: ...
    @overload
    def get_losers_bracket(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_losers_bracket(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[BracketModel]]: ...

    def get_losers_bracket(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[BracketModel]]:
        """
        Retrieve the loser's bracket for a given league.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/losers_bracket"
        bracket_json = self.client.get(endpoint)

        if not convert_results:
            return bracket_json

        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    @overload
    def get_transactions(self, league_id: str, week: int, convert_results: Literal[True]) -> List[TransactionsModel]: ...
    @overload
    def get_transactions(self, league_id: str, week: int, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_transactions(
        self, league_id: str, week: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TransactionsModel]]: ...

    def get_transactions(
        self, league_id: str, week: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TransactionsModel]]:
        """
        Retrieve transactions for a given league. Filter by week.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/transactions/{week}"
        transactions_json = self.client.get(endpoint)

        if not convert_results:
            return transactions_json

        return [TransactionsModel.from_dict(transaction_data) for transaction_data in transactions_json]

    @overload
    def get_traded_picks(self, league_id: str, convert_results: Literal[True]) -> List[TradedPickModel]: ...
    @overload
    def get_traded_picks(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_traded_picks(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TradedPickModel]]: ...

    def get_traded_picks(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TradedPickModel]]:
        """
        Retrieve traded picks for a given league.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/traded_picks"
        traded_picks_json = self.client.get(endpoint)

        if not convert_results:
            return traded_picks_json

        return [TradedPickModel.from_dict(traded_pick) for traded_pick in traded_picks_json]

    @overload
    def get_nfl_state(self, convert_results: Literal[True]) -> NFLStateModel: ...
    @overload
    def get_nfl_state(self, convert_results: Literal[False]) -> Dict: ...
    @overload
    def get_nfl_state(self, convert_results: Optional[bool] = None) -> Union[Dict, NFLStateModel]: ...

    def get_nfl_state(self, convert_results: Optional[bool] = None) -> Union[Dict, NFLStateModel]:
        """
        Get the current NFL state (season, week, etc.).

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        Returns:
            NFLStateModel or dict with current season information.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = "state/nfl"
        state_data = self.client.get(endpoint)

        if not convert_results:
            return state_data

        return NFLStateModel.from_dict(state_data)
