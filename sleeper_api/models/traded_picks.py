from typing import List, Dict, Union

class TradedPick:
    def __init__(self, season: str, round: int, roster_id: int, previous_owner_id: int, owner_id: int):
        
        # Add type checks to raise ValueError if data types are invalid
        if not isinstance(season, str):
            raise ValueError(f"Invalid type for season: expected str, got {type(season).__name__}")
        if not isinstance(round, int):
            raise ValueError(f"Invalid type for round: expected int, got {type(round).__name__}")
        if not isinstance(roster_id, int):
            raise ValueError(f"Invalid type for roster_id: expected int, got {type(roster_id).__name__}")
        if not isinstance(previous_owner_id, int):
            raise ValueError(f"Invalid type for previous_owner_id: expected int, got {type(previous_owner_id).__name__}")
        if not isinstance(owner_id, int):
            raise ValueError(f"Invalid type for owner_id: expected int, got {type(owner_id).__name__}")

        
        self.season = season
        self.round = round
        self.roster_id = roster_id
        self.previous_owner_id = previous_owner_id
        self.owner_id = owner_id

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int]]) -> 'TradedPick':
        return cls(
            season=data['season'],
            round=data['round'],
            roster_id=data['roster_id'],
            previous_owner_id=data['previous_owner_id'],
            owner_id=data['owner_id']
        )

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {
            'season': self.season,
            'round': self.round,
            'roster_id': self.roster_id,
            'previous_owner_id': self.previous_owner_id,
            'owner_id': self.owner_id
        }

    def __repr__(self):
        return (f"<TradedPick(season={self.season}, round={self.round}, roster_id={self.roster_id}, "
                f"previous_owner_id={self.previous_owner_id}, owner_id={self.owner_id})>")


class TradedDraftPicksModel:
    def __init__(self, traded_picks: List[TradedPick]):
        self.traded_picks = traded_picks

    @classmethod
    def from_list(cls, data: List[Dict[str, Union[str, int]]]) -> 'TradedDraftPicksModel':
        traded_picks = [TradedPick.from_dict(pick) for pick in data]
        return cls(traded_picks=traded_picks)

    def to_list(self) -> List[Dict[str, Union[str, int]]]:
        return [pick.to_dict() for pick in self.traded_picks]

    def __repr__(self):
        return f"<TradedDraftPicksModel(traded_picks={len(self.traded_picks)} picks)>"
