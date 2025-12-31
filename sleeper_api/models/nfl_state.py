"""NFL state model for current season/week information."""
from typing import Dict, Any


class NFLStateModel:
    """Represents the current NFL state (season, week, etc.)."""

    def __init__(
        self,
        season: str,
        week: int,
        season_type: str,
        display_week: int,
    ):
        """
        Initialize the NFL state model.

        Args:
            season: Current NFL season year (e.g., "2024").
            week: Current week number.
            season_type: Type of season ("regular", "post", "off").
            display_week: Display week number.
        """
        self.season = season
        self.week = week
        self.season_type = season_type
        self.display_week = display_week

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NFLStateModel':
        """
        Create an NFLStateModel from a dictionary.

        Args:
            data: Dictionary containing NFL state data.

        Returns:
            NFLStateModel instance.
        """
        return cls(
            season=data.get('season', ''),
            week=data.get('week', 0),
            season_type=data.get('season_type', 'regular'),
            display_week=data.get('display_week', 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the NFL state to a dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            'season': self.season,
            'week': self.week,
            'season_type': self.season_type,
            'display_week': self.display_week,
        }

    def __repr__(self):
        return (f"<NFLStateModel(season={self.season}, week={self.week}, "
                f"season_type={self.season_type})>")
