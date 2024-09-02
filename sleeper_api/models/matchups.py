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
