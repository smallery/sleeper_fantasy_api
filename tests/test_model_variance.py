"""Tests for the TeamVarianceModel class."""
from sleeper_api.models.variance import TeamVarianceModel


class TestTeamVarianceModel:
    """Test cases for TeamVarianceModel."""

    def test_initialization(self):
        """Test TeamVarianceModel initialization."""
        # Arrange & Act
        variance = TeamVarianceModel(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            weekly_scores=[100.0, 110.0, 105.0],
            mean=105.0,
            stddev=5.0,
            floor=95.0,
            ceiling=115.0,
            projection=108.0
        )

        # Assert
        assert variance.roster_id == 1
        assert variance.display_name == "John Doe"
        assert variance.team_name == "The Champions"
        assert variance.mean == 105.0
        assert variance.stddev == 5.0

    def test_from_weekly_scores_with_data(self):
        """Test creating variance from weekly scores."""
        # Arrange
        weekly_scores = [100.0, 110.0, 105.0, 115.0, 102.0]

        # Act
        variance = TeamVarianceModel.from_weekly_scores(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            weekly_scores=weekly_scores,
            projection=108.0
        )

        # Assert
        assert variance.roster_id == 1
        assert variance.mean > 0
        assert variance.stddev > 0
        assert variance.floor <= variance.mean
        assert variance.ceiling >= variance.mean
        assert variance.projection == 108.0

    def test_from_weekly_scores_insufficient_data(self):
        """Test variance calculation with insufficient data."""
        # Arrange
        weekly_scores = [100.0]  # Only one score

        # Act
        variance = TeamVarianceModel.from_weekly_scores(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            weekly_scores=weekly_scores,
            projection=108.0
        )

        # Assert
        assert variance.mean == 108.0  # Uses projection
        assert variance.stddev == 20.0  # Default
        assert variance.floor >= 0  # Non-negative

    def test_from_weekly_scores_no_data(self):
        """Test variance calculation with no data."""
        # Act
        variance = TeamVarianceModel.from_weekly_scores(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            weekly_scores=[],
            projection=105.0
        )

        # Assert
        assert variance.mean == 105.0  # Uses projection
        assert variance.stddev == 20.0  # Default
        assert variance.floor >= 0

    def test_to_dict(self):
        """Test converting variance to dictionary."""
        # Arrange
        variance = TeamVarianceModel(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            weekly_scores=[100.0, 110.0],
            mean=105.0,
            stddev=5.0,
            floor=95.0,
            ceiling=115.0,
            projection=108.0
        )

        # Act
        result = variance.to_dict()

        # Assert
        assert result["roster_id"] == 1
        assert result["display_name"] == "John Doe"
        assert result["mean"] == 105.0
        assert result["projection"] == 108.0

    def test_repr(self):
        """Test string representation."""
        # Arrange
        variance = TeamVarianceModel(
            roster_id=1,
            display_name="John Doe",
            team_name="The Champions",
            mean=105.0,
            stddev=5.0
        )

        # Act
        result = repr(variance)

        # Assert
        assert "TeamVarianceModel" in result
        assert "105.0" in result
