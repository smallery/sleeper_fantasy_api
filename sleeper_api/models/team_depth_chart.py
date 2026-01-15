"""
Model for NFL team depth charts from Sleeper API.

Note: This uses an undocumented Sleeper endpoint that may change.
"""
from typing import List, Optional, Dict, Any


class TeamDepthChartModel:
    """
    Represents an NFL team's depth chart.

    The depth chart organizes players by position, with players listed
    in order of depth (starter, backup, etc.).

    Attributes:
        # Defensive positions
        db: List of defensive back player IDs
        dl: List of defensive line player IDs
        fs: List of free safety player IDs
        lb: List of linebacker player IDs
        lcb: List of left cornerback player IDs
        lde: List of left defensive end player IDs
        ldt: List of left defensive tackle player IDs
        lolb: List of left outside linebacker player IDs
        ls: List of long snapper player IDs
        mlb: List of middle linebacker player IDs
        nb: List of nickelback player IDs
        rcb: List of right cornerback player IDs
        rde: List of right defensive end player IDs
        rdt: List of right defensive tackle player IDs
        rolb: List of right outside linebacker player IDs
        ss: List of strong safety player IDs

        # Offensive positions
        ol: List of offensive line player IDs
        qb: List of quarterback player IDs
        rb: List of running back player IDs
        te: List of tight end player IDs
        wr1: List of WR1 position player IDs
        wr2: List of WR2 position player IDs
        wr3: List of WR3 position player IDs

        # Special teams
        k: List of kicker player IDs
        p: List of punter player IDs

        team: The NFL team abbreviation (e.g., 'SF', 'KC')
    """

    def __init__(
        self,
        team: str,
        # Defensive positions
        db: Optional[List[str]] = None,
        dl: Optional[List[str]] = None,
        fs: Optional[List[str]] = None,
        lb: Optional[List[str]] = None,
        lcb: Optional[List[str]] = None,
        lde: Optional[List[str]] = None,
        ldt: Optional[List[str]] = None,
        lolb: Optional[List[str]] = None,
        ls: Optional[List[str]] = None,
        mlb: Optional[List[str]] = None,
        nb: Optional[List[str]] = None,
        rcb: Optional[List[str]] = None,
        rde: Optional[List[str]] = None,
        rdt: Optional[List[str]] = None,
        rolb: Optional[List[str]] = None,
        ss: Optional[List[str]] = None,
        # Offensive positions
        ol: Optional[List[str]] = None,
        qb: Optional[List[str]] = None,
        rb: Optional[List[str]] = None,
        te: Optional[List[str]] = None,
        wr1: Optional[List[str]] = None,
        wr2: Optional[List[str]] = None,
        wr3: Optional[List[str]] = None,
        # Special teams
        k: Optional[List[str]] = None,
        p: Optional[List[str]] = None,
    ):
        """
        Initialize a TeamDepthChartModel.

        Args:
            team: NFL team abbreviation (e.g., 'SF', 'KC')
            **kwargs: Position-specific player ID lists
        """
        self.team = team

        # Defensive positions
        self.db = db or []
        self.dl = dl or []
        self.fs = fs or []
        self.lb = lb or []
        self.lcb = lcb or []
        self.lde = lde or []
        self.ldt = ldt or []
        self.lolb = lolb or []
        self.ls = ls or []
        self.mlb = mlb or []
        self.nb = nb or []
        self.rcb = rcb or []
        self.rde = rde or []
        self.rdt = rdt or []
        self.rolb = rolb or []
        self.ss = ss or []

        # Offensive positions
        self.ol = ol or []
        self.qb = qb or []
        self.rb = rb or []
        self.te = te or []
        self.wr1 = wr1 or []
        self.wr2 = wr2 or []
        self.wr3 = wr3 or []

        # Special teams
        self.k = k or []
        self.p = p or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any], team: str) -> 'TeamDepthChartModel':
        """
        Create a TeamDepthChartModel instance from a dictionary.

        Args:
            data: Dictionary containing depth chart data from API
            team: NFL team abbreviation

        Returns:
            TeamDepthChartModel instance
        """
        return cls(
            team=team,
            # Defensive positions
            db=data.get('DB', []),
            dl=data.get('DL', []),
            fs=data.get('FS', []),
            lb=data.get('LB', []),
            lcb=data.get('LCB', []),
            lde=data.get('LDE', []),
            ldt=data.get('LDT', []),
            lolb=data.get('LOLB', []),
            ls=data.get('LS', []),
            mlb=data.get('MLB', []),
            nb=data.get('NB', []),
            rcb=data.get('RCB', []),
            rde=data.get('RDE', []),
            rdt=data.get('RDT', []),
            rolb=data.get('ROLB', []),
            ss=data.get('SS', []),
            # Offensive positions
            ol=data.get('OL', []),
            qb=data.get('QB', []),
            rb=data.get('RB', []),
            te=data.get('TE', []),
            wr1=data.get('WR1', []),
            wr2=data.get('WR2', []),
            wr3=data.get('WR3', []),
            # Special teams
            k=data.get('K', []),
            p=data.get('P', []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the TeamDepthChartModel instance to a dictionary.

        Returns:
            Dictionary representation of the depth chart
        """
        return {
            'team': self.team,
            'DB': self.db,
            'DL': self.dl,
            'FS': self.fs,
            'LB': self.lb,
            'LCB': self.lcb,
            'LDE': self.lde,
            'LDT': self.ldt,
            'LOLB': self.lolb,
            'LS': self.ls,
            'MLB': self.mlb,
            'NB': self.nb,
            'RCB': self.rcb,
            'RDE': self.rde,
            'RDT': self.rdt,
            'ROLB': self.rolb,
            'SS': self.ss,
            'OL': self.ol,
            'QB': self.qb,
            'RB': self.rb,
            'TE': self.te,
            'WR1': self.wr1,
            'WR2': self.wr2,
            'WR3': self.wr3,
            'K': self.k,
            'P': self.p,
        }

    def get_starters(self) -> Dict[str, Optional[str]]:
        """
        Get the starting player for each position.

        Returns:
            Dictionary mapping position to starting player ID (first in depth chart)
        """
        positions = {
            'QB': self.qb,
            'RB': self.rb,
            'WR1': self.wr1,
            'WR2': self.wr2,
            'WR3': self.wr3,
            'TE': self.te,
            'K': self.k,
            'P': self.p,
            'LDE': self.lde,
            'RDE': self.rde,
            'LDT': self.ldt,
            'RDT': self.rdt,
            'LOLB': self.lolb,
            'MLB': self.mlb,
            'ROLB': self.rolb,
            'LCB': self.lcb,
            'RCB': self.rcb,
            'FS': self.fs,
            'SS': self.ss,
        }

        return {pos: (players[0] if players else None) for pos, players in positions.items()}

    def __repr__(self):
        starter_count = sum(1 for players in [
            self.qb, self.rb, self.wr1, self.wr2, self.wr3, self.te,
            self.k, self.p, self.lde, self.rde, self.ldt, self.rdt,
            self.lolb, self.mlb, self.rolb, self.lcb, self.rcb, self.fs, self.ss
        ] if players)
        return f"<TeamDepthChartModel(team={self.team}, positions_filled={starter_count})>"
