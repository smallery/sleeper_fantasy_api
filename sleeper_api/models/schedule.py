"""
Model for NFL schedule data from Sleeper API.

Note: This uses an undocumented Sleeper endpoint that may change.
"""
from typing import List, Optional, Dict, Any


class ScheduleGameModel:
    """
    Represents a single NFL game in the schedule.

    Attributes:
        game_id: Unique identifier for the game
        status: Game status (e.g., 'scheduled', 'in_progress', 'final')
        date: Game date in ISO format (e.g., '2023-09-10')
        home: Home team abbreviation (e.g., 'SF', 'KC')
        away: Away team abbreviation (e.g., 'PIT', 'GB')
        week: Week number in the season
        season_type: Type of season ('regular' or 'post')
    """

    def __init__(
        self,
        game_id: str,
        status: str,
        date: str,
        home: str,
        away: str,
        week: int,
        season_type: str = 'regular'
    ):
        """
        Initialize a ScheduleGameModel.

        Args:
            game_id: Unique game identifier
            status: Game status
            date: Game date in ISO format
            home: Home team abbreviation
            away: Away team abbreviation
            week: Week number
            season_type: 'regular' or 'post'
        """
        # Validate types
        if not isinstance(game_id, str):
            raise TypeError(f"Invalid type for game_id: expected str, got {type(game_id).__name__}")
        if not isinstance(status, str):
            raise TypeError(f"Invalid type for status: expected str, got {type(status).__name__}")
        if not isinstance(date, str):
            raise TypeError(f"Invalid type for date: expected str, got {type(date).__name__}")
        if not isinstance(home, str):
            raise TypeError(f"Invalid type for home: expected str, got {type(home).__name__}")
        if not isinstance(away, str):
            raise TypeError(f"Invalid type for away: expected str, got {type(away).__name__}")
        if not isinstance(week, int):
            raise TypeError(f"Invalid type for week: expected int, got {type(week).__name__}")
        if not isinstance(season_type, str):
            raise TypeError(f"Invalid type for season_type: expected str, got {type(season_type).__name__}")

        self.game_id = game_id
        self.status = status
        self.date = date
        self.home = home
        self.away = away
        self.week = week
        self.season_type = season_type

    @classmethod
    def from_dict(cls, data: Dict[str, Any], season_type: str = 'regular') -> 'ScheduleGameModel':
        """
        Create a ScheduleGameModel instance from a dictionary.

        Args:
            data: Dictionary containing game data from API
            season_type: Type of season ('regular' or 'post')

        Returns:
            ScheduleGameModel instance
        """
        # Handle different possible field names
        game_id = data.get('game_id') or data.get('GameID') or data.get('gameId', '')
        status = data.get('status') or data.get('Status', 'scheduled')
        date = data.get('date') or data.get('Date', '')
        home = data.get('home') or data.get('Home', '')
        away = data.get('away') or data.get('Away', '')
        week = data.get('week') or data.get('Week', 0)

        return cls(
            game_id=game_id,
            status=status,
            date=date,
            home=home,
            away=away,
            week=week,
            season_type=season_type
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ScheduleGameModel instance to a dictionary.

        Returns:
            Dictionary representation of the game
        """
        return {
            'game_id': self.game_id,
            'status': self.status,
            'date': self.date,
            'home': self.home,
            'away': self.away,
            'week': self.week,
            'season_type': self.season_type
        }

    def __repr__(self):
        return (f"<ScheduleGameModel(game_id={self.game_id}, week={self.week}, "
                f"{self.away}@{self.home}, status={self.status})>")


class NFLScheduleModel:
    """
    Represents an NFL season schedule.

    Attributes:
        year: The NFL season year
        season_type: Type of season ('regular' or 'post')
        games: List of ScheduleGameModel instances
    """

    def __init__(self, year: int, season_type: str, games: List[ScheduleGameModel]):
        """
        Initialize an NFLScheduleModel.

        Args:
            year: NFL season year
            season_type: 'regular' or 'post'
            games: List of ScheduleGameModel instances
        """
        self.year = year
        self.season_type = season_type
        self.games = games

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]], year: int, season_type: str) -> 'NFLScheduleModel':
        """
        Create an NFLScheduleModel instance from a list of game dictionaries.

        Args:
            data: List of game dictionaries from API
            year: NFL season year
            season_type: 'regular' or 'post'

        Returns:
            NFLScheduleModel instance
        """
        games = [ScheduleGameModel.from_dict(game_data, season_type) for game_data in data]
        return cls(year=year, season_type=season_type, games=games)

    def get_games_by_week(self, week: int) -> List[ScheduleGameModel]:
        """
        Get all games for a specific week.

        Args:
            week: Week number

        Returns:
            List of games in that week
        """
        return [game for game in self.games if game.week == week]

    def get_games_by_team(self, team: str) -> List[ScheduleGameModel]:
        """
        Get all games for a specific team.

        Args:
            team: Team abbreviation (e.g., 'SF', 'KC')

        Returns:
            List of games involving that team
        """
        return [game for game in self.games if game.home == team or game.away == team]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the NFLScheduleModel instance to a dictionary.

        Returns:
            Dictionary representation of the schedule
        """
        return {
            'year': self.year,
            'season_type': self.season_type,
            'games': [game.to_dict() for game in self.games]
        }

    def __repr__(self):
        return f"<NFLScheduleModel(year={self.year}, season_type={self.season_type}, games={len(self.games)})>"
