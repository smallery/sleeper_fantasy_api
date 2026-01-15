from typing import Dict, List, Optional, Any

class RosterModel:
    """
    Represents a team roster in a Sleeper fantasy league.

    Attributes:
        roster_id: Unique roster identifier within the league (int)
        owner_id: User ID of the roster owner (str)
        league_id: League identifier (str)
        players: List of all player IDs on the roster (List[str])
        starters: List of starting player IDs (List[str])
        bench: List of benched player IDs (computed from players - starters) (List[str])
        reserve: List of player IDs on reserve/IR (List[str])
        settings: League-specific roster settings and standings data (Dict[str, Any])
            Common keys: wins, losses, ties, fpts (total fantasy points),
                        fpts_against, fpts_decimal, etc.

    Note:
        - The 'starters' list is automatically filtered to only include valid player IDs
          (removes placeholder '0' values that sometimes appear in API responses)
        - The 'bench' list is computed as players not in starters

    Example:
        >>> roster = RosterModel.from_dict(roster_data)
        >>> print(f"Roster {roster.roster_id} - Owner: {roster.owner_id}")
        >>> print(f"Starters: {len(roster.starters)}, Bench: {len(roster.bench)}")
        >>> wins = roster.settings.get('wins', 0)
        >>> losses = roster.settings.get('losses', 0)
    """
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
        # Add type validation checks here
        if not isinstance(starters, list) or not all(isinstance(s, str) for s in starters):
            raise ValueError(f"Invalid type for 'starters': expected List[str], got {type(starters).__name__}")
        
        if not isinstance(settings, dict):
            raise ValueError(f"Invalid type for 'settings': expected Dict, got {type(settings).__name__}")
        
        if not isinstance(roster_id, int):
            raise ValueError(f"Invalid type for 'roster_id': expected int, got {type(roster_id).__name__}")
        
        if not isinstance(reserve, list) or not all(isinstance(r, str) for r in reserve):
            raise ValueError(f"Invalid type for 'reserve': expected List[str], got {type(reserve).__name__}")
        
        if not isinstance(players, list) or not all(isinstance(p, str) for p in players):
            raise ValueError(f"Invalid type for 'players': expected List[str], got {type(players).__name__}")
        
        if not isinstance(owner_id, str):
            raise ValueError(f"Invalid type for 'owner_id': expected str, got {type(owner_id).__name__}")
        
        if not isinstance(league_id, str):
            raise ValueError(f"Invalid type for 'league_id': expected str, got {type(league_id).__name__}")
        
        self.starters = [player_id for player_id in starters if player_id in players] # filters out 0's that sometimes show up
        self.settings = settings
        self.roster_id = roster_id
        self.reserve = reserve
        self.players = players
        self.owner_id = owner_id
        self.league_id = league_id
        self.bench = [player_id for player_id in players if player_id not in starters]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RosterModel':
        """
        Create a RosterModel instance from a dictionary.
        """
        return cls(
            starters=data['starters'],
            settings=data['settings'],
            roster_id=data['roster_id'],
            reserve=data['reserve'] or [],
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

