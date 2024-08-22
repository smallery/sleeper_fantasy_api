from typing import List, Optional
from datetime import datetime
from ..models.user import UserModel
from ..models.league import LeagueModel
from ..exceptions import SleeperAPIError

class UserEndpoint:
    def __init__(self, client):
        self.client = client

    def get_user(self, user_id:str = None, username:str = None) -> UserModel:
        """
        Retrieve user information by user_id or username.

        :param user_id: The ID of the user (optional).
        :param username: The username of the user (optional).
        :return: The user information as a dictionary.
        :raises: SleeperAPIError if neither user_id nor username is provided.
        """
        if not user_id and not username:
            raise SleeperAPIError("You must provide either user_id or username.")

        endpoint = f"user/{user_id}" if user_id else f"user/{username}"
        user_data = self.client.get(endpoint)

        return UserModel.from_json(user_data)
    
    def fetch_nfl_leagues(self, user:UserModel, season: Optional[int] = None, all_seasons:bool = False) -> None:
        """
        Retrieve all of the leagues for a given user

        :param sport: the name of the sport, currently only nfl is supported.
        :param season: the season to retrieve all leagues from
        :return: a list of all of the leagues for a given year
        :raises: SleeperAPIError if no leagues are found
        """
        current_year = datetime.now().year
        sport = 'nfl'
        leagues_data = []

        if not all_seasons:
            season = season or current_year
            if season < 2015 or season > current_year:
                raise SleeperAPIError(f"Sleeper API only has data from the 2015 season through the {current_year} season.")
            
            endpoint = f"user/{user.user_id}/leagues/{sport}/{season}"
            leagues_data = self.client.get(endpoint)
            if not leagues_data:
                raise SleeperAPIError(f"No League data found for the {season} season.")
        else:
            for season in range(2015, current_year + 1):
                endpoint = f"user/{user.user_id}/leagues/{sport}/{season}"
                league_season = self.client.get(endpoint)
                leagues_data.extend(league_season)

        nfl_leagues = [LeagueModel.from_json(league) for league in leagues_data]

        user.nfl_leagues = nfl_leagues
