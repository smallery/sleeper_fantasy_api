"""Tests for the ProjectionsEndpoint class."""
import pytest
from unittest.mock import Mock
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

    def test_get_player_projection_found(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projection for a single player."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {
            "player1": {"pts_ppr": 15.5, "rec": 5, "rec_yd": 60},
            "player2": {"pts_ppr": 12.0, "rush_yd": 80}
        }
        mock_client.get.return_value = api_data

        # Act
        result = projections_endpoint.get_player_projection("player1", 2024, 1)

        # Assert
        assert result == {"pts_ppr": 15.5, "rec": 5, "rec_yd": 60}

    def test_get_player_projection_not_found(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projection for player not in dataset."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5}}
        mock_client.get.return_value = api_data

        # Act
        result = projections_endpoint.get_player_projection("player999", 2024, 1)

        # Assert
        assert result is None

    def test_get_player_projection_uses_cache(self, projections_endpoint, mock_cache):
        """Test that get_player_projection uses cached data."""
        # Arrange
        cached_data = {
            "player1": {"pts_ppr": 15.5, "pass_yd": 300},
            "player2": {"pts_ppr": 10.0}
        }
        mock_cache.get.return_value = cached_data

        # Act
        result = projections_endpoint.get_player_projection("player1", 2024, 1)

        # Assert
        assert result == {"pts_ppr": 15.5, "pass_yd": 300}
        mock_cache.get.assert_called_once_with("projections:2024:1")
