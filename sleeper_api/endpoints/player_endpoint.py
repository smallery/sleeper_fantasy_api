"""
This module provides the `PlayerEndpoint` class for interacting
with player-related API endpoints of the Sleeper API.
"""
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from platformdirs import user_cache_dir

from ..config import CACHE_DURATION, CONVERT_RESULTS
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

    def get_all_players(
            self, sport = 'nfl', convert_results = CONVERT_RESULTS
            ) -> Union[Dict[str, Dict], List[PlayerModel]]:
        """
        Retrieve all players, either from the cache or by making an API call.
        """
        if self._is_cache_valid():
            players_json = self._load_cache()
        else:
            endpoint = f"players/{sport}"
            players_json = self.client.get(endpoint)
            self._save_cache(players_json)

        if not convert_results:
            return players_json

        players = [
            PlayerModel.from_dict(player_data) for player_id,player_data in list(players_json.items())
            ]
        return players

    def get_trending_players(
            self, trend_type: str, sport: str = 'nfl', lookback_hours: Optional[int] = 24,
            limit: Optional[int] = 25, convert_results=CONVERT_RESULTS
            ) -> Union[List[Dict[str, Any]], List[PlayerModel]]:
        """
        Retrieve trending players based on adds or drops.

        :param sport: The sport, such as 'nfl'.
        :param trend_type: Either 'add' or 'drop'.
        :param lookback_hours: Number of hours to look back (default is 24).
        :param limit: Number of results you want (default is 25).
        :return: A list of PlayerModel instances if convert_results is True, or the raw data if False.
        """
        if trend_type not in ('add', 'drop'):
            raise SleeperAPIError("Trend type must either be add or drop.")

        endpoint = f"players/{sport}/trending/{trend_type}?lookback_hours={lookback_hours}&limit={limit}"
        trending_data = self.client.get(endpoint)

        if not convert_results:
            return trending_data

        # If convert_results is True, map the trending data to PlayerModel instances
        # NOTE: this passes convert_results positionally, which actually lands in
        # get_all_players' `sport` parameter, not its own convert_results -- a
        # pre-existing bug left untouched here since fixing it would change
        # get_all_players' effective sport argument (a behavior change out of
        # scope for the CI-gate work in issue #20). get_all_players' own
        # convert_results still defaults to True, so this reliably returns
        # List[PlayerModel] in practice, which is what the cast below asserts.
        all_players = cast(List[PlayerModel], self.get_all_players(convert_results))
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

    def get_player(self,player_id):
        """
        Returns a specific playerModel for the player ID
        """
        for player in self.get_all_players():
            if player.player_id == player_id:
                return player

        raise SleeperAPIError(f"Player_ID: {player_id} Not Found")

    def search_players(self, search_keys: Dict[str, Any], convert_results=CONVERT_RESULTS):
        """
        Search for players based on complex criteria using a combination of AND/OR logic and comparison operators.

        This function retrieves all player data and filters it according to the search keys provided.
        The search keys can include various logical conditions (AND/OR) and comparison operators
        (e.g., '==', '!=', '>', '<', '>=', '<=', 'in', 'not in') for different attributes of the player data.
        """
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
        # No convert_results passed, so this uses the CONVERT_RESULTS default
        # (True) -- always a List[PlayerModel] in practice.
        for player in cast(List[PlayerModel], self.get_all_players()):
            if player.team_abbr == team_abbr:
                team_players.append(player)

        #raise SleeperAPIError("Player Not Found")
        return team_players
