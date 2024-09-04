import unittest
from unittest.mock import MagicMock
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.models.user import UserModel
from sleeper_api.models.league import LeagueModel

class TestIntegration(unittest.TestCase):

    def setUp(self):
        # Mock the client that will be passed to the UserEndpoint and LeagueEndpoint
        self.client = MagicMock()
        self.user_endpoint = UserEndpoint(self.client)
        self.league_endpoint = LeagueEndpoint(self.client)

    def test_full_user_league_workflow(self):
        # Mock user data response from API
        mock_user_response = {
            "username": "sleeperuser",
            "user_id": "12345678",
            "display_name": "SleeperUser",
            "avatar": "cc12ec49965eb7856f84d71cf85306af"
        }
        self.client.get.return_value = mock_user_response

        # Call get_user and assert that the user model is properly created
        user = self.user_endpoint.get_user(user_id="12345678")
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.user_id, "12345678")
        self.assertEqual(user.username, "sleeperuser")

        # Mock league data response from API
        mock_league_response = [{
            "league_id": "123",
            "name": "Best League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 10,
            "roster_positions": ["QB", "RB", "WR", "TE", "FLEX", "K", "DEF"],
            "settings": {"playoff_teams": 4},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0}
        }]
        self.client.get.return_value = mock_league_response

        # Call fetch_nfl_leagues and assert that league data is correctly added to the user model
        self.user_endpoint.fetch_nfl_leagues(user=user, season=2023)
        self.assertEqual(len(user.nfl_leagues), 1)
        league = user.nfl_leagues[0]
        self.assertIsInstance(league, LeagueModel)
        self.assertEqual(league.league_id, "123")
        self.assertEqual(league.name, "Best League")

    def test_get_league_workflow(self):
        # Mock league data
        mock_league_response = {
            "league_id": "123",
            "name": "Best League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 10,
            "roster_positions": ["QB", "RB", "WR", "TE", "FLEX", "K", "DEF"],
            "settings": {"playoff_teams": 4},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0}
        }
        self.client.get.return_value = mock_league_response

        # Call get_league from LeagueEndpoint
        league = self.league_endpoint.get_league(league_id="123")
        self.assertIsInstance(league, LeagueModel)
        self.assertEqual(league.league_id, "123")
        self.assertEqual(league.name, "Best League")
        self.assertEqual(league.sport, "nfl")
        self.assertEqual(league.season, "2023")

if __name__ == '__main__':
    unittest.main()
