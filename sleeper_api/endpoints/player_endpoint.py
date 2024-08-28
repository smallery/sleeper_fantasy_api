# import os
import gzip
import json
from pathlib import Path
from platformdirs import user_cache_dir
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..models.player import PlayerModel
from ..exceptions import SleeperAPIError
from ..config import CACHE_DURATION

class PlayerEndpoint:

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

    def _load_cache(self) -> List[Dict]:
        """
        Load player data from the cache file.
        """
        with gzip.open(self.cache_file, 'rt') as f:
            return json.load(f)

        return data

    def _save_cache(self, players_json: List[Dict]):
        """
        Save player data to the cache file.
        """
        try:
            with gzip.open(self.cache_file, 'wt') as f:
                json.dump(players_json, f, indent=4)
        except IOError as e:
            print(f"Warning: Could not save cache file: {e}")

    def get_all_players(self, sport = 'nfl', convert_results = True) -> List[PlayerModel]:
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

        players = [PlayerModel.from_dict(player_data) for player_id,player_data in list(players_json.items())]
        return players


    def get_trending_players(self, sport: str, trend_type: str, lookback_hours: Optional[int] = 24
                             , limit: Optional[int] = 25, convert_results = True) -> List[Dict[str, int]]:
            """
            Retrieve trending players based on adds or drops.

            :param sport: The sport, such as 'nfl'.
            :param trend_type: Either 'add' or 'drop'.
            :param lookback_hours: Number of hours to look back (default is 24).
            :param limit: Number of results you want (default is 25).
            :return: A list of dictionaries containing 'player_id' and 'count'.
            """
            if trend_type not in ('add','drop'):
                raise SleeperAPIError("Trend type must either be add or drop.")
            
            endpoint = f"players/{sport}/trending/{trend_type}?lookback_hours={lookback_hours}&limit={limit}"
            trending_data = self.client.get(endpoint)
        
            if not convert_results:
                return trending_data
            
            #  If convert_results is True, map the trending data to PlayerModel instances
            all_players = self.get_all_players(convert_results)
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
        # returns a specific playerModel for the player ID
        pass

    def search_players(self,query):
        # query will be attributes and values and this will return a list of players or player models that match
        pass

    def get_players_by_team(self,team_abbr):
        # use the query to return a list of player models where the team_abbr matches the player team_abbr
        pass