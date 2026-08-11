from typing import Dict, List, Optional


class DraftModel:
    def __init__(
        self,
        # from_json() validates these are present in the raw dict before
        # calling this constructor, but does so via `data[field] is None`
        # checks on `data` rather than on these already-extracted locals, so
        # mypy can't narrow them back to non-Optional here. Widened to match
        # what data.get(...) actually returns.
        draft_id: Optional[str] = None,
        league_id: Optional[str] = None,
        season: Optional[str] = None,
        status: Optional[str] = None,
        draft_order: Optional[Dict[int, str]] = None,
        picks: Optional[List[Dict]] = None,
    ):
        self.draft_id = str(draft_id)
        self.league_id = str(league_id)
        self.season = season
        self.status = status
        self.draft_order = draft_order or {}
        self.picks = picks or []

    @classmethod
    def from_json(cls, data: Dict):

        # Check if required fields are present
        required_fields = ['draft_id', 'league_id', 'season', 'status', 'draft_order']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise TypeError(f"Missing required field: {field}")

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
