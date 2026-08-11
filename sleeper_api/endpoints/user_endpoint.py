from typing import Dict, List, Optional, Union, cast

from ..config import CONVERT_RESULTS, get_current_season
from ..exceptions import SleeperAPIError, UserNotFoundError
from ..models.draft import DraftModel
from ..models.league import LeagueModel
from ..models.user import UserModel
from .draft_endpoint import DraftEndpoint

class UserEndpoint:
    '''
    Class to interact with the user endpoint more easily
    '''
    def __init__(self, client):
        self.client = client

    def get_user(
        self, user_id: Optional[str] = None, username: Optional[str] = None, convert_results: bool = CONVERT_RESULTS
    ) -> Union[Dict, UserModel]:
        """
        Retrieve user information by user_id or username.

        A caller who looks a user up by name or ID asked about a specific,
        named resource -- a 404 here means that resource does not exist, not
        "nothing to report", so this raises rather than returning None (see
        issue #17). Contrast with e.g. get_matchups(), where a missing
        result for a given week is a normal, expected outcome.

        :param user_id: The ID of the user (optional).
        :param username: The username of the user (optional).
        :return: The user information as a dictionary.
        :raises SleeperAPIError: if neither user_id nor username is provided.
        :raises UserNotFoundError: if the given user_id/username does not exist.
        """
        if not user_id and not username:
            raise SleeperAPIError("You must provide either user_id or username.")

        endpoint = f"user/{user_id}" if user_id else f"user/{username}"
        user_data = self.client.get(endpoint)

        if user_data is None:
            raise UserNotFoundError(user_id or username)

        if not convert_results:
            return user_data

        return UserModel.from_json(user_data)

    def fetch_nfl_leagues(
        self, user_id: str, season: Optional[int] = None, convert_results: bool = CONVERT_RESULTS
    ) -> Union[List[Dict], List[LeagueModel]]:
        """
        Retrieve all of the leagues for a given user in a specific season.

        A user simply having no leagues in a season is a normal outcome, not
        an error -- this returns [] rather than raising (see issue #21,
        which used to raise SleeperAPIError here and collided badly with the
        wrong default season in issue #18 firing routinely for months at a
        time).

        :param user_id: The ID of the user.
        :param season: The season to retrieve all leagues from. Defaults to
            the current season, resolved via get_current_season() against
            GET /state/nfl (not the calendar year -- see issue #18). During
            preseason that resolves to the *previous* season, since the
            upcoming one has no league data yet.
        :return: A list of all of the leagues for the given year, or []
            if the user has none.
        :raises: SleeperAPIError if the requested season is out of range.
        """
        current_season = get_current_season(self.client)
        season_to_fetch = season if season is not None else current_season
        sport = 'nfl'

        if season_to_fetch < 2015 or season_to_fetch > current_season:
            raise SleeperAPIError(f"Sleeper API only has data from the 2015 season through the {current_season} season.")

        endpoint = f"user/{user_id}/leagues/{sport}/{season_to_fetch}"
        leagues_data = self.client.get(endpoint)

        if not leagues_data:
            return []

        if not convert_results:
            return leagues_data

        return [LeagueModel.from_json(league) for league in leagues_data]

    def get_all_drafts(self, user_id: str, sport: str = 'nfl', season: Optional[int] = None, convert_results: bool = CONVERT_RESULTS) -> Union[List[Dict], List[DraftModel]]:
        """
        Retrieve all drafts for a user for a given season, default is the current season.

        :param user_id: The ID of the user.
        :param sport: The name of the sport, currently only nfl is supported.
        :param season: The season to retrieve all drafts from. Defaults to
            the current season, resolved via get_current_season() against
            GET /state/nfl (not the calendar year -- see issue #18). During
            preseason that resolves to the *previous* season -- pass season
            explicitly if you specifically want the upcoming season's draft.
        :return: A list of all of the draft models for the given season.
        :raises: SleeperAPIError if no drafts are found.
        """
        season_to_fetch = season if season is not None else get_current_season(self.client)
        endpoint = f"user/{user_id}/drafts/{sport}/{season_to_fetch}"
        draft_data = self.client.get(endpoint)

        if not draft_data:
            raise SleeperAPIError(f"No draft data found for the {season_to_fetch} season.")

        if not convert_results:
            return draft_data

        # Optionally lookup full draft details by ID if draft order is missing
        draft_ids = [draft['draft_id'] for draft in draft_data]
        draft_endpoint = DraftEndpoint(self.client)

        # No convert_results passed to get_draft_by_id, so it uses the
        # CONVERT_RESULTS default (True) -- always a DraftModel in practice.
        return [cast(DraftModel, draft_endpoint.get_draft_by_id(draft_id)) for draft_id in draft_ids]
