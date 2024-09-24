"""
This module provides the `UserEndpoint` class for interacting 
with user-related API endpoints of the Sleeper API.
"""
from typing import List, Optional
from ..models.user import UserModel
from ..models.league import LeagueModel
from ..models.draft import DraftModel
from .draft_endpoint import DraftEndpoint
from ..exceptions import SleeperAPIError
from ..config import CONVERT_RESULTS, DEFAULT_SEASON

class UserEndpoint:
    '''
    Class to interact with the user endpoint more easily
    '''
    def __init__(self, client):
        self.client = client

    def get_user(self, user_id:str = None, username:str = None, convert_results = CONVERT_RESULTS) -> UserModel:
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

        if not convert_results:
            return user_data

        return UserModel.from_json(user_data)

    def fetch_nfl_leagues(self, user_id: str, season: Optional[int] = None, all_seasons:bool = False, convert_results = CONVERT_RESULTS):
        """
        Retrieve all of the leagues for a given user

        :param sport: the name of the sport, currently only nfl is supported.
        :param season: the season to retrieve all leagues from
        :return: a list of all of the leagues for a given year
        :raises: SleeperAPIError if no leagues are found
        """
        current_season = DEFAULT_SEASON
        sport = 'nfl'
        leagues_data = []

        if not all_seasons:
            season_to_fetch = season or current_season
            if season_to_fetch < 2015 or season_to_fetch > current_season:
                raise SleeperAPIError(f"Sleeper API only has data from the 2015 season through the {current_season} season.")

            endpoint = f"user/{user_id}/leagues/{sport}/{season_to_fetch}"
            leagues_data = self.client.get(endpoint)
            if not leagues_data:
                raise SleeperAPIError(f"No League data found for the {season_to_fetch} season.")
        else:
            for season_year in range(2015, current_season + 1):
                endpoint = f"user/{user_id}/leagues/{sport}/{season_year}"
                league_season = self.client.get(endpoint)
                leagues_data.extend(league_season)

        if not convert_results:
            return leagues_data
        
        return [LeagueModel.from_json(league) for league in leagues_data]
        

    def get_all_drafts(self, user_id, sport:str = 'nfl', season = DEFAULT_SEASON, convert_results = CONVERT_RESULTS) -> List[DraftModel]:
        """
        Retrieve all of the for a user for a given season, default is the current season

        :param sport: the name of the sport, currently only nfl is supported.
        :param season: the season to retrieve all leagues from, default is current year
        :return: a list of all of the draft models for the given season
        :raises: SleeperAPIError if no drafts are found
        """
        endpoint = f"user/{user_id}/drafts/{sport}/{season}"
        draft_data = self.client.get(endpoint)

        if not draft_data:
            raise SleeperAPIError(f"No League data found for the {season} season.")
        
        if not convert_results:
            return draft_data
        
        # to improve data for draft endpoint, this sometimes doesn't return draft_order attribute
        # so I do a lookup on ID instead to get the full set of required fields
        draft_ids = [draft['draft_id'] for draft in draft_data]
        
        draft_enpoint = DraftEndpoint(self.client)

        return [draft_enpoint.get_draft_by_id(draft_id) for draft_id in draft_ids]
    