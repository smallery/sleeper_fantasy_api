from typing import Dict, List, Optional

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

    