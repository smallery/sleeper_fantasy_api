from typing import List, Dict
from ..models.draft import DraftModel
from ..models.picks import PicksModel
from ..models.traded_picks import TradedDraftPicksModel
from ..config import CONVERT_RESULTS, DEFAULT_SEASON
from sleeper_api.exceptions import SleeperAPIError

# TO DO: set up results as objects for the draft
class DraftEndpoint:
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

    def get_drafts_by_league(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[DraftModel]:
        """
        Retrieve all drafts for a specific league.
        """
        endpoint = f"league/{league_id}/drafts"
        drafts_json = self.client.get(endpoint)
        
        if not convert_results:
            return drafts_json
        
        return [DraftModel.from_json(draft) for draft in drafts_json]
    
    def get_drafts_by_user(self, user_id: str, sport: str = 'nfl', season: int = DEFAULT_SEASON, convert_results = CONVERT_RESULTS) -> List[DraftModel]:
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
