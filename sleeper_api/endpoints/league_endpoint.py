from typing import Dict, List, Optional
from datetime import datetime
from ..models.league import LeagueModel
from ..models.user import UserModel
from ..exceptions import SleeperAPIError
from .user_endpoint import UserEndpoint

class LeagueEndpoint:
    def __init__(self, client):
        self.client = client

    def get_league(self, league_id: str) -> LeagueModel:
        """
        Retrieve a specific league by its ID.
        """
        endpoint = f"league/{league_id}"
        league_data = self.client.get(endpoint)
        return LeagueModel.from_json(league_data)

    def get_rosters(self, league: LeagueModel) -> List[Dict]:
        """
        Retrieve the rosters for a given league.
        """
        endpoint = f"league/{league.league_id}/rosters"
        return self.client.get(endpoint)

    def get_users(self, league: LeagueModel, convert_results = True) -> List[Dict]:
        """
        Retrieve the users in a given league.
        Returns a list of users. 
            - If convert_results = False, this will be the raw JSON.
            - If convert_results = True, then this will be a list of user model objects
        """
        endpoint = f"league/{league.league_id}/users"
        user_data_json_list = self.client.get(endpoint)
        
        if convert_results == False:
            # note: the username will be missing from these user records, this can be retrieved if needed
            return [UserModel.from_json(user_data)for user_data in user_data_json_list]
        else: 
            return user_data_json_list
            

    def get_matchups(self, league: LeagueModel, week: int) -> List[Dict]:
        """
        Retrieve the matchups for a given league and week.
        """
        endpoint = f"league/{league.league_id}/matchups/{week}"
        return self.client.get(endpoint)

    def get_winners_bracket(self, league: LeagueModel) -> List[Dict]:
        """
        Retrieve the winner's bracket for a given league.
        """
        endpoint = f"league/{league.league_id}/winners_bracket"
        return self.client.get(endpoint)

    def get_losers_bracket(self, league: LeagueModel) -> List[Dict]:
        """
        Retrieve the loser's bracket for a given league.
        """
        endpoint = f"league/{league.league_id}/losers_bracket"
        return self.client.get(endpoint)

    def get_transactions(self, league: LeagueModel, week: Optional[int] = None) -> List[Dict]:
        """
        Retrieve transactions for a given league. Optionally filter by week.
        """
        endpoint = f"league/{league.league_id}/transactions"
        if week is not None:
            endpoint += f"/{week}" # I'm not sure if we're able to exclude weeks...
        return self.client.get(endpoint)

    def get_traded_picks(self, league: LeagueModel) -> List[Dict]:
        """
        Retrieve traded picks for a given league.
        """
        endpoint = f"league/{league.league_id}/traded_picks"
        return self.client.get(endpoint)