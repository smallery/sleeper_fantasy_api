"""Team variance model for historical scoring analysis."""
import statistics
from typing import List, Dict, Any


class TeamVarianceModel:
    """Historical scoring variance for a team."""

    def __init__(
        self,
        roster_id: int,
        display_name: str,
        team_name: str,
        weekly_scores: List[float] = None,
        mean: float = 0.0,
        stddev: float = 0.0,
        floor: float = 0.0,
        ceiling: float = 0.0,
        projection: float = 0.0,
    ):
        """
        Initialize the team variance model.

        Args:
            roster_id: Team's roster ID.
            display_name: Owner's display name.
            team_name: Team name.
            weekly_scores: List of weekly scores.
            mean: Average weekly score.
            stddev: Standard deviation of scores.
            floor: Scoring floor (mean - 2*stddev, bounded by min).
            ceiling: Scoring ceiling (mean + 2*stddev, bounded by max).
            projection: Current week projection.
        """
        self.roster_id = roster_id
        self.display_name = display_name
        self.team_name = team_name
        self.weekly_scores = weekly_scores or []
        self.mean = mean
        self.stddev = stddev
        self.floor = floor
        self.ceiling = ceiling
        self.projection = projection

    @classmethod
    def from_weekly_scores(
        cls,
        roster_id: int,
        display_name: str,
        team_name: str,
        weekly_scores: List[float],
        projection: float = 0.0,
    ) -> 'TeamVarianceModel':
        """
        Create TeamVarianceModel from a list of weekly scores.

        Args:
            roster_id: Team's roster ID.
            display_name: Owner's display name.
            team_name: Team name.
            weekly_scores: List of weekly scores.
            projection: Current week projection.

        Returns:
            TeamVarianceModel with calculated statistics.
        """
        if len(weekly_scores) < 2:
            # Not enough data for variance calculation
            mean = projection if projection > 0 else 100.0
            stddev = 20.0
            scores_min = mean - 40
            scores_max = mean + 40
        else:
            mean = statistics.mean(weekly_scores)
            stddev = statistics.stdev(weekly_scores)
            scores_min = min(weekly_scores)
            scores_max = max(weekly_scores)

        # Calculate floor and ceiling bounded by 2 stddev
        floor = max(scores_min, mean - 2 * stddev)
        ceiling = min(scores_max, mean + 2 * stddev)

        # Ensure non-negative floor and reasonable ceiling
        floor = max(0.0, floor)
        ceiling = max(ceiling, floor + 10)

        return cls(
            roster_id=roster_id,
            display_name=display_name,
            team_name=team_name,
            weekly_scores=weekly_scores,
            mean=round(mean, 2),
            stddev=round(stddev, 2),
            floor=round(floor, 2),
            ceiling=round(ceiling, 2),
            projection=round(projection, 2),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            'roster_id': self.roster_id,
            'display_name': self.display_name,
            'team_name': self.team_name,
            'weekly_scores': self.weekly_scores,
            'mean': self.mean,
            'stddev': self.stddev,
            'floor': self.floor,
            'ceiling': self.ceiling,
            'projection': self.projection,
        }

    def __repr__(self):
        return (f"<TeamVarianceModel(roster_id={self.roster_id}, "
                f"mean={self.mean}, stddev={self.stddev})>")
