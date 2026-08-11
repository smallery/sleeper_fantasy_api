"""
This module provides the `PlayerEndpoint` class for interacting
with player-related API endpoints of the Sleeper API.
"""
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union, cast, overload

from platformdirs import user_cache_dir

from ..config import CACHE_DURATION
from ..exceptions import SleeperAPIError
from ..models.player import PlayerModel

# Comparison operators supported by PlayerEndpoint.search_players()'s filter
# syntax (e.g. {"age": {">": 25}}). Pulled out to a dispatch table instead of
# an if/elif chain so the mccabe complexity of safe_search_type stays under
# the project's max-complexity=15 gate without changing which operators are
# supported or how they behave.
_SEARCH_OPERATORS = {
    "==": lambda record_value, val: record_value == val,
    "!=": lambda record_value, val: record_value != val,
    ">": lambda record_value, val: record_value > val,
    "<": lambda record_value, val: record_value < val,
    ">=": lambda record_value, val: record_value >= val,
    "<=": lambda record_value, val: record_value <= val,
    "in": lambda record_value, val: record_value in val,
    "not in": lambda record_value, val: record_value not in val,
}


class PlayerEndpoint:
    """
    Player endpoint class to enable easy interactions with the API for player info

    Every method's ``convert_results`` parameter defaults to the owning
    `SleeperClient`'s `convert_results` setting when omitted (``None``) --
    see issue #24. Pass it explicitly to override that default for a single
    call.
    """
    def __init__(self, client, cache_file=None):
        self.client = client
        self.cache_file = cache_file
        self.cache_duration = CACHE_DURATION

        if cache_file is None:
            cache_dir = Path(user_cache_dir(appname="sleeper_api", appauthor="smallery"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = cache_dir / 'players_cache.json.gz'
        else:
            self.cache_file = Path(cache_file)

    def _is_cache_valid(self) -> bool:
        """
        Check if the cached player data is still valid (i.e., less than a day old).
        """
        if not self.cache_file.exists():
            return False

        cache_mtime = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        return datetime.now() - cache_mtime < self.cache_duration

    def _load_cache(self) -> Dict[str, Dict]:
        """
        Load player data from the cache file.
        """
        with gzip.open(self.cache_file, 'rt') as f:
            return json.load(f)

    def _save_cache(self, players_json: Dict[str, Dict]):
        """
        Save player data to the cache file.
        """
        try:
            with gzip.open(self.cache_file, 'wt') as f:
                json.dump(players_json, f, indent=4)
        except IOError as e:
            print(f"Warning: Could not save cache file: {e}")

    @overload
    def get_all_players(self, sport: str = 'nfl', *, convert_results: Literal[True]) -> List[PlayerModel]: ...
    @overload
    def get_all_players(self, sport: str, convert_results: Literal[True]) -> List[PlayerModel]: ...
    @overload
    def get_all_players(self, sport: str = 'nfl', *, convert_results: Literal[False]) -> Dict[str, Dict]: ...
    @overload
    def get_all_players(self, sport: str, convert_results: Literal[False]) -> Dict[str, Dict]: ...
    @overload
    def get_all_players(
        self, sport: str = 'nfl', convert_results: Optional[bool] = None
    ) -> Union[Dict[str, Dict], List[PlayerModel]]: ...

    def get_all_players(
            self, sport: str = 'nfl', convert_results: Optional[bool] = None
            ) -> Union[Dict[str, Dict], List[PlayerModel]]:
        """
        Retrieve all players, either from the cache or by making an API call.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results

        players_json = self._load_cache() if self._is_cache_valid() else None

        # A cached payload that isn't a player mapping is unusable. This is not
        # hypothetical: until issue #21 was fixed, get_trending_players() passed
        # convert_results positionally into `sport`, so this method fetched
        # `players/True`, got a 404 (i.e. None), and cached that. Anyone who ran
        # an earlier version therefore has a poisoned cache file, and loading it
        # blindly raised AttributeError on the .items() call below. Treat a
        # non-mapping cache as a miss and re-fetch instead.
        if not isinstance(players_json, dict):
            endpoint = f"players/{sport}"
            players_json = self.client.get(endpoint)
            # Only cache a usable response, so a bad fetch cannot poison the
            # cache for every later call the way it used to.
            if isinstance(players_json, dict):
                self._save_cache(players_json)
            else:
                raise SleeperAPIError(
                    f"Expected a player mapping from {endpoint}, got "
                    f"{type(players_json).__name__}"
                )

        if not convert_results:
            return players_json

        players = [
            PlayerModel.from_dict(player_data) for player_id,player_data in list(players_json.items())
            ]
        return players

    @overload
    def get_trending_players(
        self, trend_type: str, sport: str = 'nfl', lookback_hours: Optional[int] = 24,
        limit: Optional[int] = 25, *, convert_results: Literal[True]
    ) -> List[PlayerModel]: ...
    @overload
    def get_trending_players(
        self, trend_type: str, sport: str, lookback_hours: Optional[int],
        limit: Optional[int], convert_results: Literal[True]
    ) -> List[PlayerModel]: ...
    @overload
    def get_trending_players(
        self, trend_type: str, sport: str = 'nfl', lookback_hours: Optional[int] = 24,
        limit: Optional[int] = 25, *, convert_results: Literal[False]
    ) -> List[Dict[str, Any]]: ...
    @overload
    def get_trending_players(
        self, trend_type: str, sport: str, lookback_hours: Optional[int],
        limit: Optional[int], convert_results: Literal[False]
    ) -> List[Dict[str, Any]]: ...
    @overload
    def get_trending_players(
        self, trend_type: str, sport: str = 'nfl', lookback_hours: Optional[int] = 24,
        limit: Optional[int] = 25, convert_results: Optional[bool] = None
    ) -> Union[List[Dict[str, Any]], List[PlayerModel]]: ...

    def get_trending_players(
            self, trend_type: str, sport: str = 'nfl', lookback_hours: Optional[int] = 24,
            limit: Optional[int] = 25, convert_results: Optional[bool] = None
            ) -> Union[List[Dict[str, Any]], List[PlayerModel]]:
        """
        Retrieve trending players based on adds or drops.

        :param sport: The sport, such as 'nfl'.
        :param trend_type: Either 'add' or 'drop'.
        :param lookback_hours: Number of hours to look back (default is 24).
        :param limit: Number of results you want (default is 25).
        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        :return: A list of PlayerModel instances if convert_results is True, or the raw data if False.
        """
        if trend_type not in ('add', 'drop'):
            raise SleeperAPIError("Trend type must either be add or drop.")

        if convert_results is None:
            convert_results = self.client.convert_results

        # Query params go through the client's params= (which requests
        # URL-encodes), not hand-built into the path -- interpolating values
        # directly into the endpoint string skipped encoding entirely, so any
        # future string-valued parameter containing '&', '=', or a space
        # would have corrupted the query (see issue #21).
        endpoint = f"players/{sport}/trending/{trend_type}"
        trending_data = self.client.get(
            endpoint, params={"lookback_hours": lookback_hours, "limit": limit}
        )
        # Sleeper 404s when the collection does not exist for these
        # arguments, which the client surfaces as None. Return an empty
        # collection instead of leaking it: the raw path would otherwise
        # hand back None against a declared List[...], and the convert
        # path raised "'NoneType' object is not iterable".
        if trending_data is None:
            return []


        if not convert_results:
            return trending_data

        # If convert_results is True, map the trending data to PlayerModel instances.
        # Both args must be passed as keywords: get_all_players()'s signature is
        # (sport='nfl', convert_results=...), so a positional call here
        # silently landed convert_results in the `sport` slot instead (it went
        # unnoticed because the cache-hit path never uses `sport`; a cache miss
        # would have requested players/True from the API). Keyword args also let
        # trending players for a non-nfl sport get looked up against player data
        # for the *same* sport, rather than always defaulting to 'nfl'.
        # The `not convert_results` early return above means we can only reach
        # here with convert_results True; passing it as a keyword literal True
        # lets the @overload on get_all_players() narrow the result to
        # List[PlayerModel] without a cast.
        all_players = self.get_all_players(sport=sport, convert_results=True)
        player_dict = {player.player_id: player for player in all_players}

        result = []
        for entry in trending_data:
            player_id = entry['player_id']
            if player_id in player_dict:
                player = player_dict[player_id]
                if trend_type == 'add':
                    player.add_count = entry['count']
                elif trend_type == 'drop':
                    player.drop_count = entry['count']
                result.append(player)

        return result

    def get_player(self, player_id: str) -> PlayerModel:
        """
        Returns a specific playerModel for the player ID
        """
        for player in self.get_all_players(convert_results=True):
            if player.player_id == player_id:
                return player

        raise SleeperAPIError(f"Player_ID: {player_id} Not Found")

    @overload
    def search_players(self, search_keys: Dict[str, Any], *, convert_results: Literal[True]) -> List[PlayerModel]: ...
    @overload
    def search_players(self, search_keys: Dict[str, Any], convert_results: Literal[True]) -> List[PlayerModel]: ...
    @overload
    def search_players(self, search_keys: Dict[str, Any], *, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def search_players(self, search_keys: Dict[str, Any], convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def search_players(
        self, search_keys: Dict[str, Any], convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[PlayerModel]]: ...

    def search_players(
        self, search_keys: Dict[str, Any], convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[PlayerModel]]:
        """
        Search for players based on complex criteria using a combination of AND/OR logic and comparison operators.

        This function retrieves all player data and filters it according to the search keys provided.
        The search keys can include various logical conditions (AND/OR) and comparison operators
        (e.g., '==', '!=', '>', '<', '>=', '<=', 'in', 'not in') for different attributes of the player data.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results

        def safe_search_type(record, key, value):
            record_value = record.get(key)

            if record_value is None:
                return False  # Skip records where the value is None

            if not isinstance(value, dict):
                return record_value == value

            for operator, val in value.items():
                try:
                    comparator = _SEARCH_OPERATORS[operator]
                except KeyError:
                    raise ValueError(f"Unsupported operator: {operator}") from None
                if not comparator(record_value, val):
                    return False
            return True

        # Recursive function to handle AND/OR logic
        def evaluate_conditions(record, conditions):
            if isinstance(conditions, dict):
                if "AND" in conditions:
                    return all(evaluate_conditions(record, cond) for cond in conditions["AND"])
                elif "OR" in conditions:
                    return any(evaluate_conditions(record, cond) for cond in conditions["OR"])
                else:
                    return all(safe_search_type(record, k, v) for k, v in conditions.items())
            else:
                raise ValueError(f"Unsupported conditions format: {conditions}")

        # Load all player data. convert_results=False guarantees the
        # Dict[str, Dict] branch of get_all_players' Union return type.
        all_players_json = cast(Dict[str, Dict], self.get_all_players(convert_results=False))
        player_data_list = []

        # removes the key from the all_players json so it's just a list of player json data
        # this makes it easier to search and transform into a PlayerModel
        for key, value in all_players_json.items():
            value['key'] = key
            player_data_list.append(value)

        # Filter players based on the complex search keys
        filtered_player_json = [
            record for record in player_data_list
            if evaluate_conditions(record, search_keys)
        ]

        # Return the results in the desired format
        if not convert_results:
            return filtered_player_json

        return [PlayerModel.from_dict(data) for data in filtered_player_json]

    def get_players_by_team(self,team_abbr) -> List[PlayerModel]:
        '''use the query to return a list of player models where the team_abbr matches the player team_abbr'''
        team_players = []
        # convert_results=True passed explicitly, so the @overload on
        # get_all_players() narrows this to List[PlayerModel] with no cast.
        for player in self.get_all_players(convert_results=True):
            if player.team_abbr == team_abbr:
                team_players.append(player)

        #raise SleeperAPIError("Player Not Found")
        return team_players
