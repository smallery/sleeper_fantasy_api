from typing import Optional, Union, Dict, Any

class BracketModel:
    def __init__(
        self,
        r: int,                # Round for this matchup (1st, 2nd, 3rd round, etc.)
        m: int,                # Match id of the matchup (unique within a bracket)
        t1: Optional[Union[int, Dict[str, int]]] = None,  # Roster_id of team 1 OR {w: match_id}
        t2: Optional[Union[int, Dict[str, int]]] = None,  # Roster_id of team 2 OR {l: match_id}
        w: Optional[int] = None,          # Roster_id of the winning team (if match has been played)
        l: Optional[int] = None,          # Roster_id of the losing team (if match has been played)
        t1_from: Optional[Dict[str, int]] = None,  # Where t1 comes from (either winner or loser of a match id)
        t2_from: Optional[Dict[str, int]] = None,  # Where t2 comes from (either winner or loser of a match id)
        p: Optional[int] = None          # Optional placeholder for specific positions in the bracket (e.g., 1st, 3rd)
    ):
        self.round = r
        self.match_id = m
        self.team1 = t1
        self.team2 = t2
        self.winner = w
        self.loser = l
        self.team1_from = t1_from
        self.team2_from = t2_from
        self.position = p

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BracketModel':
        """
        Create a BracketModel instance from a dictionary.
        """
        return cls(
            r=data['r'],
            m=data['m'],
            t1=data.get('t1'),
            t2=data.get('t2'),
            w=data.get('w'),
            l=data.get('l'),
            t1_from=data.get('t1_from'),
            t2_from=data.get('t2_from'),
            p=data.get('p')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the BracketModel instance to a dictionary.
        """
        return {
            'r': self.round,
            'm': self.match_id,
            't1': self.team1,
            't2': self.team2,
            'w': self.winner,
            'l': self.loser,
            't1_from': self.team1_from,
            't2_from': self.team2_from,
            'p': self.position
        }

    def __repr__(self):
        return f"<BracketModel(round={self.round}, match={self.match_id}, t1={self.team1}, t2={self.team2}, winner={self.winner}, loser={self.loser}, position={self.position})>"
