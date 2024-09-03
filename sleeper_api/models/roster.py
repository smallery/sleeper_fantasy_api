from typing import Dict, List, Optional, Any

class RosterModel:
    def __init__(
        self,
        starters: List[str],
        settings: Dict[str, Any],
        roster_id: int,
        reserve: List[str],
        players: List[str],
        owner_id: str,
        league_id: str
    ):
        self.starters = starters
        self.settings = settings
        self.roster_id = roster_id
        self.reserve = reserve
        self.players = players
        self.owner_id = owner_id
        self.league_id = league_id

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RosterModel':
        """
        Create a RosterModel instance from a dictionary.
        """
        return cls(
            starters=data['starters'],
            settings=data['settings'],
            roster_id=data['roster_id'],
            reserve=data['reserve'],
            players=data['players'],
            owner_id=data['owner_id'],
            league_id=data['league_id']
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the RosterModel instance to a dictionary.
        """
        return {
            'starters': self.starters,
            'settings': self.settings,
            'roster_id': self.roster_id,
            'reserve': self.reserve,
            'players': self.players,
            'owner_id': self.owner_id,
            'league_id': self.league_id
        }

    def __repr__(self):
        return (f"<RosterModel(roster_id={self.roster_id}, owner_id={self.owner_id}, league_id={self.league_id})>")
