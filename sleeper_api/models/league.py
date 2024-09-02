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

class LeagueModel:
    def __init__(
        self,
        league_id: str,
        name: str,
        status: str,
        sport: str,
        season: str,
        season_type: str,
        total_rosters: int,
        roster_positions: List[str],
        settings: Dict[str, int],
        scoring_settings: Dict[str, float],
        metadata: Optional[Dict[str, str]] = None,
        avatar: Optional[str] = None,
        draft_id: Optional[str] = None,
        bracket_id: Optional[int] = None,
        loser_bracket_id: Optional[int] = None,
        group_id: Optional[str] = None,
        last_message_id: Optional[str] = None,
        last_author_id: Optional[str] = None,
        last_author_display_name: Optional[str] = None,
        last_author_avatar: Optional[str] = None,
        last_message_time: Optional[int] = None,
        last_transaction_id: Optional[str] = None,
        previous_league_id: Optional[str] = None,
    ):
        self.league_id = league_id
        self.name = name
        self.status = status
        self.sport = sport
        self.season = season
        self.season_type = season_type
        self.total_rosters = total_rosters
        self.roster_positions = roster_positions
        self.settings = settings
        self.scoring_settings = scoring_settings
        self.metadata = metadata or {}
        self.avatar = avatar
        self.draft_id = draft_id
        self.bracket_id = bracket_id
        self.loser_bracket_id = loser_bracket_id
        self.group_id = group_id
        self.last_message_id = last_message_id
        self.last_author_id = last_author_id
        self.last_author_display_name = last_author_display_name
        self.last_author_avatar = last_author_avatar
        self.last_message_time = last_message_time
        self.last_transaction_id = last_transaction_id
        self.previous_league_id = previous_league_id

        ## -- still deciding if I want to allow this object to store this data
        self.rosters: Optional[List[Dict]] = None
        self.users: Optional[List[Dict]] = None
        self.matchups: Optional[Dict[int, List[Dict]]] = {}
        self.winners_bracket: Optional[List[Dict]] = None
        self.losers_bracket: Optional[List[Dict]] = None
        self.transactions: Optional[Dict[int, List[Dict]]] = {}
        self.traded_picks: Optional[List[Dict]] = None

    @classmethod
    def from_json(cls, data: Dict):
        return cls(
            league_id=data.get('league_id'),
            name=data.get('name'),
            status=data.get('status'),
            sport=data.get('sport'),
            season=data.get('season'),
            season_type=data.get('season_type'),
            total_rosters=data.get('total_rosters'),
            roster_positions=data.get('roster_positions', []),
            settings=data.get('settings', {}),
            scoring_settings=data.get('scoring_settings', {}),
            metadata=data.get('metadata', {}),
            avatar=data.get('avatar'),
            draft_id=data.get('draft_id'),
            bracket_id=data.get('bracket_id'),
            loser_bracket_id=data.get('loser_bracket_id'),
            group_id=data.get('group_id'),
            last_message_id=data.get('last_message_id'),
            last_author_id=data.get('last_author_id'),
            last_author_display_name=data.get('last_author_display_name'),
            last_author_avatar=data.get('last_author_avatar'),
            last_message_time=data.get('last_message_time'),
            last_transaction_id=data.get('last_transaction_id'),
            previous_league_id=data.get('previous_league_id'),
        )

    def __repr__(self):
        return f"<LeagueModel(name={self.name}, season={self.season}, league_id={self.league_id})>"

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
