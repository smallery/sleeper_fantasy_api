from typing import List, Dict, Optional
from ..models.draft import DraftModel
from ..exceptions import SleeperAPIError
from ..config import CONVERT_RESULTS

class DraftEndpoint:
    def __init__(self, client):
        self.client = client

    def get_draft(self, draft_id: str) -> DraftModel:
        """
        Retrieve a specific draft by its ID.
        """
        endpoint = f"draft/{draft_id}"
        draft_data = self.client.get(endpoint)
        return DraftModel.from_json(draft_data)

    def get_drafts_by_league(self, league_id: str) -> List[DraftModel]:
        """
        Retrieve all drafts for a specific league.
        """
        endpoint = f"league/{league_id}/drafts"
        drafts_json = self.client.get(endpoint)
        return [DraftModel.from_json(draft) for draft in drafts_json]

    def get_draft_picks(self, draft_id: str) -> List[Dict]:
        """
        Retrieve all picks made in a specific draft.
        """
        endpoint = f"draft/{draft_id}/picks"
        return self.client.get(endpoint)

    def get_draft_order(self, draft_id: str) -> Dict[int, str]:
        """
        Retrieve the draft order for a specific draft.
        """
        endpoint = f"draft/{draft_id}/order"
        return self.client.get(endpoint)

    def get_traded_picks(self, draft_id: str) -> List[Dict]:
        """
        Retrieve all traded picks in a specific draft.
        """
        endpoint = f"draft/{draft_id}/traded_picks"
        return self.client.get(endpoint)
