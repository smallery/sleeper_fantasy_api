"""
This module provides the `DraftEndpoint` class for interacting with draft-related 
API endpoints of the Sleeper API.

The `DraftEndpoint` class includes methods for retrieving draft information,
draft picks, and traded picks. It supports fetching drafts by ID, by league,
and by user, as well as handling the conversion of results into model instances.

Classes:
---------
- `DraftEndpoint`: Contains methods for accessing draft data from the Sleeper API.

Usage:
------
To use the `DraftEndpoint` class, instantiate it with an API client and call its methods 
to retrieve draft-related data:

    >>> from your_module import DraftEndpoint
    >>> client = YourAPIClient()  # Replace with actual client
    >>> draft_endpoint = DraftEndpoint(client)

    # Example usage
    >>> draft = draft_endpoint.get_draft_by_id('draft_id')
    >>> drafts = draft_endpoint.get_drafts_by_league('league_id')
    >>> user_drafts = draft_endpoint.get_drafts_by_user('user_id')
    >>> picks = draft_endpoint.get_draft_picks('draft_id')
    >>> traded_picks = draft_endpoint.get_traded_picks('draft_id')

Exception Handling:
-------------------
- `SleeperAPIError`: Raised for API errors and invalid responses.

"""


from typing import List, Dict
from ..models.draft import DraftModel
from ..models.picks import PicksModel
from ..models.traded_picks import TradedDraftPicksModel
from ..config import CONVERT_RESULTS, DEFAULT_SEASON

# TO DO: set up results as objects for the draft
class DraftEndpoint:
    """
    Provides methods for interacting with draft-related API endpoints of the Sleeper API.

    The `DraftEndpoint` class supports retrieving draft data, including specific drafts,
    drafts by league or user, draft picks, and traded picks. 
    Results can be converted into model instances based on the specified parameters.

    Methods:
    --------
    - `get_draft_by_id(draft_id):
        Retrieves a specific draft by its ID. Optionally converts the result into a `DraftModel`.

    - `get_drafts_by_league(league_id):
        Retrieves all drafts for a specific league. Optionally converts the results 
        into a list of `DraftModel` instances.

    - `get_drafts_by_user(
            user_id: str, sport: str = 'nfl', season: int = DEFAULT_SEASON
            , convert_results: bool = CONVERT_RESULTS) -> List[DraftModel]`:
        Retrieves all drafts for a specific user in a given season. Optionally converts 
        the results into a list of `DraftModel` instances.

    - `get_draft_picks(draft_id: str, convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves all picks made in a specific draft. Optionally converts the results 
        into a list of `PicksModel` instances.

    - `get_traded_picks(draft_id: int, convert_results: bool = CONVERT_RESULTS) -> List[Dict]`:
        Retrieves all traded picks in a specific draft. Optionally converts the 
        results into a list of `TradedDraftPicksModel` instances.

    Attributes:
    -----------
    - `client`: An instance of the API client used to make requests to the Sleeper API.

    Exception Handling:
    -------------------
    - `SleeperAPIError`: Raised for API errors and invalid responses.

    Usage:
    -------
    To use the `DraftEndpoint` class, initialize it with an API client and call its methods:

        >>> client = YourAPIClient()  # Replace with actual client
        >>> draft_endpoint = DraftEndpoint(client)
        >>> draft = draft_endpoint.get_draft_by_id('draft_id')

    """
    def __init__(self, client):
        self.client = client

    def get_draft_by_id(self, draft_id: str, convert_results = CONVERT_RESULTS) -> DraftModel:
        """
        Retrieve a specific draft by its ID.
        """
        endpoint = f"draft/{draft_id}"
        draft_json = self.client.get(endpoint)

        if not convert_results:
            return draft_json

        return DraftModel.from_json(draft_json)

    def get_drafts_by_league(self, league_id: str,
                             convert_results = CONVERT_RESULTS
                             ) -> List[DraftModel]:
        """
        Retrieve all drafts for a specific league.
        """
        endpoint = f"league/{league_id}/drafts"
        drafts_json = self.client.get(endpoint)

        if not convert_results:
            return drafts_json

        return [DraftModel.from_json(draft) for draft in drafts_json]

    def get_drafts_by_user(self, user_id: str, sport: str = 'nfl',
                           season: int = DEFAULT_SEASON, convert_results = CONVERT_RESULTS
                           ) -> List[DraftModel]:
        """
        Retrieve all drafts for a specific user in a given season.
        """
        endpoint = f"user/{user_id}/drafts/{sport}/{season}"
        drafts_json = self.client.get(endpoint)

        if not convert_results:
            return drafts_json

        return [DraftModel.from_json(draft) for draft in drafts_json]

    def get_draft_picks(self, draft_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve all picks made in a specific draft.
        """
        endpoint = f"draft/{draft_id}/picks"
        picks_json = self.client.get(endpoint)

        if not convert_results:
            return picks_json

        return [PicksModel.from_dict(pick) for pick in picks_json]

    def get_traded_picks(self, draft_id: int, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve all traded picks in a specific draft.
        """
        endpoint = f"draft/{draft_id}/traded_picks"
        traded_pick_json = self.client.get(endpoint)

        if not convert_results:
            return traded_pick_json

        # Ensure we are passing the right data to TradedDraftPicksModel
        return TradedDraftPicksModel.from_list(traded_pick_json)
