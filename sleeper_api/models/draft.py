from typing import List, Dict, Optional

class DraftModel:
    def __init__(
        self,
        draft_id: str,
        league_id: str,
        season: str,
        status: str,
        draft_order: Dict[int, str],
        picks: Optional[List[Dict]] = None,
    ):
        self.draft_id = draft_id
        self.league_id = league_id
        self.season = season
        self.status = status
        self.draft_order = draft_order
        self.picks = picks or []

    @classmethod
    def from_json(cls, data: Dict):
        return cls(
            draft_id=data.get('draft_id'),
            league_id=data.get('league_id'),
            season=data.get('season'),
            status=data.get('status'),
            draft_order=data.get('draft_order', {}),
            picks=data.get('picks', [])
        )

    def __repr__(self):
        return f"<DraftModel(draft_id={self.draft_id}, league_id={self.league_id}, season={self.season})>"
