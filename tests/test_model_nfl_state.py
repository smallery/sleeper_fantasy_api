"""Tests for the NFLStateModel class."""
from sleeper_api.models.nfl_state import NFLStateModel


class TestNFLStateModel:
    """Test cases for NFLStateModel."""

    def test_initialization(self):
        """Test NFLStateModel initialization."""
        # Arrange & Act
        state = NFLStateModel(
            season="2024",
            week=12,
            season_type="regular",
            display_week=12
        )

        # Assert
        assert state.season == "2024"
        assert state.week == 12
        assert state.season_type == "regular"
        assert state.display_week == 12

    def test_from_dict(self):
        """Test creating NFLStateModel from dictionary."""
        # Arrange
        data = {
            "season": "2024",
            "week": 12,
            "season_type": "regular",
            "display_week": 12
        }

        # Act
        state = NFLStateModel.from_dict(data)

        # Assert
        assert state.season == "2024"
        assert state.week == 12
        assert state.season_type == "regular"

    def test_to_dict(self):
        """Test converting NFLStateModel to dictionary."""
        # Arrange
        state = NFLStateModel(
            season="2024",
            week=12,
            season_type="regular",
            display_week=12
        )

        # Act
        result = state.to_dict()

        # Assert
        assert result == {
            "season": "2024",
            "week": 12,
            "season_type": "regular",
            "display_week": 12
        }

    def test_repr(self):
        """Test string representation."""
        # Arrange
        state = NFLStateModel(
            season="2024",
            week=12,
            season_type="regular",
            display_week=12
        )

        # Act
        result = repr(state)

        # Assert
        assert "NFLStateModel" in result
        assert "2024" in result
        assert "12" in result
