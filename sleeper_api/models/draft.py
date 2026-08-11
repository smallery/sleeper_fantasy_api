from typing import Dict, List, Optional


class DraftModel:
    def __init__(
        self,
        # No `= None` default here: these are required arguments and
        # DraftModel() must keep raising TypeError for missing arguments,
        # same as before mypy was added. Optional[...] (without a default)
        # only describes the *type* -- from_json() supplies these via
        # data.get(...), which mypy correctly types as Optional since the
        # Sleeper payload has no schema guarantee -- it does not make the
        # argument omittable.
        draft_id: Optional[str],
        league_id: Optional[str],
        season: Optional[str],
        status: Optional[str],
        draft_order: Optional[Dict[int, str]],
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
