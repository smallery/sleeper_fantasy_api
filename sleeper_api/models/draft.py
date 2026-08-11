from typing import Dict, List, Optional, cast


class DraftModel:
    def __init__(
        self,
        # Required and non-Optional. No `= None` default, so DraftModel()
        # still raises TypeError for missing arguments; and no Optional[...],
        # because from_json() rejects None for every one of these before it
        # constructs. Publishing Optional here would force downstream callers
        # into None guards for a state that cannot exist -- the data.get()
        # uncertainty is narrowed at the parsing boundary instead (see the
        # cast(...) calls in from_json).
        draft_id: str,
        league_id: str,
        season: str,
        status: str,
        draft_order: Dict[int, str],
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

        # The loop above already rejected a missing or None value for each of
        # these, so cast away the Optional that data.get() implies rather than
        # widening the constructor's contract to match the parser's ignorance.
        return cls(
            draft_id=cast(str, data.get('draft_id')),
            league_id=cast(str, data.get('league_id')),
            season=cast(str, data.get('season')),
            status=cast(str, data.get('status')),
            draft_order=cast(Dict[int, str], data.get('draft_order', {})),
            picks=data.get('picks', [])
        )

    def __repr__(self):
        return f"<DraftModel(draft_id={self.draft_id}, league_id={self.league_id}, season={self.season})>"
