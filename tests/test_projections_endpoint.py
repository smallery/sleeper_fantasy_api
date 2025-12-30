"""Tests for the ProjectionsEndpoint class."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
from sleeper_api.persistent_cache import PersistentCache
from sleeper_api.exceptions import SleeperAPIError


class TestProjectionsEndpoint:
    """Test cases for ProjectionsEndpoint."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock SleeperClient."""
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        """Create a mock PersistentCache."""
        return Mock(spec=PersistentCache)

    @pytest.fixture
    def projections_endpoint(self, mock_client, mock_cache):
        """Create a ProjectionsEndpoint instance with mocked dependencies."""
        return ProjectionsEndpoint(mock_client, mock_cache)

    def test_get_projections_from_cache(self, projections_endpoint, mock_cache):
        """Test getting projections from cache."""
        # Arrange
        cached_data = {"player1": {"pts_ppr": 15.5}}
        mock_cache.get.return_value = cached_data

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == cached_data
        mock_cache.get.assert_called_once_with("projections:2024:1")

    def test_get_projections_from_api(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projections from API when not cached."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0}}
        mock_client.get.return_value = api_data

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == api_data
        mock_client.get.assert_called_once_with("projections/nfl/regular/2024/1")
        mock_cache.set.assert_called_once_with("projections:2024:1", api_data, ttl_hours=1.0)

    def test_get_projections_graceful_degradation(self, projections_endpoint, mock_client, mock_cache):
        """Test that failed projection fetch returns empty dict."""
        # Arrange
        mock_cache.get.return_value = None
        mock_client.get.side_effect = SleeperAPIError("API error", status_code=500)

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == {}

    def test_get_scoring_type_ppr(self, projections_endpoint, mock_client):
        """Test scoring type detection for PPR league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 1.0}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_ppr"

    def test_get_scoring_type_half_ppr(self, projections_endpoint, mock_client):
        """Test scoring type detection for half-PPR league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 0.5}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_half_ppr"

    def test_get_scoring_type_standard(self, projections_endpoint, mock_client):
        """Test scoring type detection for standard league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 0.0}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_std"

    def test_calculate_team_projection(self, projections_endpoint):
        """Test calculating team projection from starters."""
        # Arrange
        starters = ["player1", "player2", "player3"]
        projections = {
            "player1": {"pts_ppr": 15.5},
            "player2": {"pts_ppr": 12.3},
            "player3": {"pts_ppr": 8.7},
        }

        # Act
        result = projections_endpoint.calculate_team_projection(
            starters, projections, "pts_ppr"
        )

        # Assert
        assert result == 36.5

    def test_calculate_team_projection_with_missing_players(self, projections_endpoint):
        """Test team projection when some players have no projections."""
        # Arrange
        starters = ["player1", "player2", "player3"]
        projections = {
            "player1": {"pts_ppr": 15.5},
            # player2 missing
            "player3": {"pts_ppr": 8.7},
        }

        # Act
        result = projections_endpoint.calculate_team_projection(
            starters, projections, "pts_ppr"
        )

        # Assert
        assert result == 24.2  # Only counts player1 and player3

    def test_get_player_position_defense(self, projections_endpoint):
        """Test position detection for defense."""
        # Arrange
        all_players = {}

        # Act
        result = projections_endpoint.get_player_position("SF", all_players)

        # Assert
        assert result == "DEF"

    def test_get_player_position_regular(self, projections_endpoint):
        """Test position detection for regular player."""
        # Arrange
        all_players = {
            "player123": {"position": "QB"}
        }

        # Act
        result = projections_endpoint.get_player_position("player123", all_players)

        # Assert
        assert result == "QB"

    def test_calculate_optimal_lineup(self, projections_endpoint):
        """Test optimal lineup calculation for Best Ball."""
        # Arrange
        roster_players = ["qb1", "rb1", "rb2", "wr1", "wr2"]
        projections = {
            "qb1": {"pts_ppr": 20.0},
            "rb1": {"pts_ppr": 15.0},
            "rb2": {"pts_ppr": 12.0},
            "wr1": {"pts_ppr": 14.0},
            "wr2": {"pts_ppr": 10.0},
        }
        roster_positions = ["QB", "RB", "RB", "WR", "WR", "FLEX"]
        all_players = {
            "qb1": {"position": "QB"},
            "rb1": {"position": "RB"},
            "rb2": {"position": "RB"},
            "wr1": {"position": "WR"},
            "wr2": {"position": "WR"},
        }

        # Act
        starters, total = projections_endpoint.calculate_optimal_lineup(
            roster_players, projections, roster_positions, all_players, "pts_ppr"
        )

        # Assert
        assert total == 71.0  # All players should be used
        assert len(starters) == 6
        assert "qb1" in starters  # Best QB
        assert "rb1" in starters  # Best RB
        assert "rb2" in starters  # 2nd best RB
