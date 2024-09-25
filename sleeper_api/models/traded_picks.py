from typing import Dict, Union

class TradedPickModel:
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
    def from_dict(cls, data: Dict[str, Union[str, int]]) -> 'TradedPickModel':
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
        return (f"<TradedPickModel(season={self.season}, round={self.round}, roster_id={self.roster_id}, "
                f"previous_owner_id={self.previous_owner_id}, owner_id={self.owner_id})>")
    
