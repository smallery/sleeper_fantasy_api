from typing import List, Optional, Dict, Any

class MatchupModel:
    def __init__(
        self,
        starters: List[str],
        roster_id: int,
        players: List[str],
        matchup_id: int,
        points: float,
        custom_points: Optional[float] = None
    ):
        
        # Validate types
        if not isinstance(starters, list) or not all(isinstance(s, str) for s in starters):
            raise TypeError(f"Invalid type for starters: expected List[str], got {type(starters).__name__}")
        if not isinstance(roster_id, int):
            raise TypeError(f"Invalid type for roster_id: expected int, got {type(roster_id).__name__}")
        if not isinstance(players, list) or not all(isinstance(p, str) for p in players):
            raise TypeError(f"Invalid type for players: expected List[str], got {type(players).__name__}")
        if not isinstance(matchup_id, int):
            raise TypeError(f"Invalid type for matchup_id: expected int, got {type(matchup_id).__name__}")
        if not isinstance(points, (float, int)):  # Allow both float and int, but convert to float
            raise TypeError(f"Invalid type for points: expected float, got {type(points).__name__}")
        if custom_points is not None and not isinstance(custom_points, (float, int)):  # Allow None or float/int
            raise TypeError(f"Invalid type for custom_points: expected Optional[float], got {type(custom_points).__name__}")


        self.starters = starters
        self.roster_id = roster_id
        self.players = players
        self.matchup_id = matchup_id
        self.points = points
        self.custom_points = custom_points

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MatchupModel':
        """
        Create a MatchupModel instance from a dictionary.
        """
        return cls(
            starters=data['starters'],
            roster_id=data['roster_id'],
            players=data['players'],
            matchup_id=data['matchup_id'],
            points=data['points'],
            custom_points=data.get('custom_points')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the MatchupModel instance to a dictionary.
        """
        return {
            'starters': self.starters,
            'roster_id': self.roster_id,
            'players': self.players,
            'matchup_id': self.matchup_id,
            'points': self.points,
            'custom_points': self.custom_points
        }

    def __repr__(self):
        return (f"<MatchupModel(matchup_id={self.matchup_id}, roster_id={self.roster_id}, "
                f"points={self.points}, custom_points={self.custom_points})>")
