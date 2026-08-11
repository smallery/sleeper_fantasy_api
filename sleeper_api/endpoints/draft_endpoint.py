"""
This module provides the `DraftEndpoint` class for interacting with draft-related
API endpoints of the Sleeper API.

The `DraftEndpoint` class includes methods for retrieving draft information,
draft picks, and traded picks. It supports fetching drafts by ID, by league,
and by user, as well as handling the conversion of results into model instances.

"""


from typing import Dict, List, Literal, Optional, Union, overload

from ..config import get_current_season
from ..models.draft import DraftModel
from ..models.picks import PicksModel
from ..models.traded_picks import TradedPickModel


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
            user_id: str, sport: str = 'nfl', season: Optional[int] = None
            , convert_results: Optional[bool] = None) -> List[DraftModel]`:
        Retrieves all drafts for a specific user in a given season (defaults to the
        current season, resolved via GET /state/nfl). Optionally converts
        the results into a list of `DraftModel` instances.

    - `get_draft_picks(draft_id: str, convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves all picks made in a specific draft. Optionally converts the results
        into a list of `PicksModel` instances.

    - `get_traded_picks(draft_id: int, convert_results: Optional[bool] = None) -> List[Dict]`:
        Retrieves all traded picks in a specific draft. Optionally converts the
        results into a list of `TradedDraftPicksModel` instances.

    Every method's ``convert_results`` parameter defaults to the owning
    `SleeperClient`'s `convert_results` setting when omitted (``None``) --
    see issue #24. Pass it explicitly to override that default for a single
    call.

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

    @overload
    def get_draft_by_id(self, draft_id: str, convert_results: Literal[True]) -> DraftModel: ...
    @overload
    def get_draft_by_id(self, draft_id: str, convert_results: Literal[False]) -> Dict: ...
    @overload
    def get_draft_by_id(self, draft_id: str, convert_results: Optional[bool] = None) -> Union[Dict, DraftModel]: ...

    def get_draft_by_id(self, draft_id: str, convert_results: Optional[bool] = None) -> Union[Dict, DraftModel]:
        """
        Retrieve a specific draft by its ID.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"draft/{draft_id}"
        draft_json = self.client.get(endpoint)

        if not convert_results:
            return draft_json

        return DraftModel.from_json(draft_json)

    @overload
    def get_drafts_by_league(self, league_id: str, convert_results: Literal[True]) -> List[DraftModel]: ...
    @overload
    def get_drafts_by_league(self, league_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_drafts_by_league(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[DraftModel]]: ...

    def get_drafts_by_league(
        self, league_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[DraftModel]]:
        """
        Retrieve all drafts for a specific league.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"league/{league_id}/drafts"
        drafts_json = self.client.get(endpoint)
        # Sleeper 404s when the collection does not exist for these
        # arguments, which the client surfaces as None. Return an empty
        # collection instead of leaking it: the raw path would otherwise
        # hand back None against a declared List[...], and the convert
        # path raised "'NoneType' object is not iterable".
        if drafts_json is None:
            return []


        if not convert_results:
            return drafts_json

        return [DraftModel.from_json(draft) for draft in drafts_json]

    @overload
    def get_drafts_by_user(
        self, user_id: str, sport: str = 'nfl', season: Optional[int] = None, *, convert_results: Literal[True]
    ) -> List[DraftModel]: ...
    @overload
    def get_drafts_by_user(
        self, user_id: str, sport: str, season: Optional[int], convert_results: Literal[True]
    ) -> List[DraftModel]: ...
    @overload
    def get_drafts_by_user(
        self, user_id: str, sport: str = 'nfl', season: Optional[int] = None, *, convert_results: Literal[False]
    ) -> List[Dict]: ...
    @overload
    def get_drafts_by_user(
        self, user_id: str, sport: str, season: Optional[int], convert_results: Literal[False]
    ) -> List[Dict]: ...
    @overload
    def get_drafts_by_user(
        self, user_id: str, sport: str = 'nfl', season: Optional[int] = None,
        convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[DraftModel]]: ...

    def get_drafts_by_user(
        self, user_id: str, sport: str = 'nfl', season: Optional[int] = None,
        convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[DraftModel]]:
        """
        Retrieve all drafts for a specific user in a given season.

        :param season: Defaults to the current season, resolved via
            get_current_season() against GET /state/nfl (not the calendar
            year -- see issue #18). Unlike fetch_nfl_leagues()/projections,
            this defaults to the *upcoming* season during preseason rather
            than the previous one -- drafts happen during a season's own
            preseason window, so "the current season" for a draft lookup
            means the one about to be played. Pass season explicitly to
            override.
        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results

        season_to_fetch = (
            season if season is not None
            else get_current_season(self.client, prefer_previous_during_preseason=False)
        )
        endpoint = f"user/{user_id}/drafts/{sport}/{season_to_fetch}"
        drafts_json = self.client.get(endpoint)
        # Sleeper 404s when the collection does not exist for these
        # arguments, which the client surfaces as None. Return an empty
        # collection instead of leaking it: the raw path would otherwise
        # hand back None against a declared List[...], and the convert
        # path raised "'NoneType' object is not iterable".
        if drafts_json is None:
            return []


        if not convert_results:
            return drafts_json
        # to improve data for draft endpoint, this sometimes doesn't return draft_order
        # so I do a lookup on ID instead to get the full dataset
        draft_ids = [draft['draft_id'] for draft in drafts_json]

        # get_draft_by_id() is called with convert_results=True explicitly,
        # so the @overload on it already narrows this to DraftModel.
        return [self.get_draft_by_id(draft_id, convert_results=True) for draft_id in draft_ids]

    @overload
    def get_draft_picks(self, draft_id: str, convert_results: Literal[True]) -> List[PicksModel]: ...
    @overload
    def get_draft_picks(self, draft_id: str, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_draft_picks(
        self, draft_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[PicksModel]]: ...

    def get_draft_picks(
        self, draft_id: str, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[PicksModel]]:
        """
        Retrieve all picks made in a specific draft.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"draft/{draft_id}/picks"
        picks_json = self.client.get(endpoint)
        # Sleeper 404s when the collection does not exist for these
        # arguments, which the client surfaces as None. Return an empty
        # collection instead of leaking it: the raw path would otherwise
        # hand back None against a declared List[...], and the convert
        # path raised "'NoneType' object is not iterable".
        if picks_json is None:
            return []


        if not convert_results:
            return picks_json

        return [PicksModel.from_dict(pick) for pick in picks_json]

    @overload
    def get_traded_picks(self, draft_id: int, convert_results: Literal[True]) -> List[TradedPickModel]: ...
    @overload
    def get_traded_picks(self, draft_id: int, convert_results: Literal[False]) -> List[Dict]: ...
    @overload
    def get_traded_picks(
        self, draft_id: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TradedPickModel]]: ...

    def get_traded_picks(
        self, draft_id: int, convert_results: Optional[bool] = None
    ) -> Union[List[Dict], List[TradedPickModel]]:
        """
        Retrieve all traded picks in a specific draft.

        :param convert_results: If omitted, uses the owning client's
            `convert_results` default.
        """
        if convert_results is None:
            convert_results = self.client.convert_results
        endpoint = f"draft/{draft_id}/traded_picks"
        traded_pick_json = self.client.get(endpoint)
        # Sleeper 404s when the collection does not exist for these
        # arguments, which the client surfaces as None. Return an empty
        # collection instead of leaking it: the raw path would otherwise
        # hand back None against a declared List[...], and the convert
        # path raised "'NoneType' object is not iterable".
        if traded_pick_json is None:
            return []


        if not convert_results:
            return traded_pick_json

        # Ensure we are passing the right data to TradedDraftPicksModel
        return [TradedPickModel.from_dict(traded_pick) for traded_pick in traded_pick_json]
