import unittest
from unittest.mock import MagicMock
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.models.user import UserModel
from sleeper_api.models.league import LeagueModel
from sleeper_api.exceptions import SleeperAPIError

class TestUserEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = UserEndpoint(self.client)

    def test_get_user_success(self):
        # Mock the API response for a valid user
        mock_response = {
            "username": "sleeperuser",
            "user_id": "12345678",
            "display_name": "SleeperUser",
            "avatar": "cc12ec49965eb7856f84d71cf85306af"
        }
        self.client.get.return_value = mock_response

        # Call get_user and assert that the returned user is correct
        user = self.endpoint.get_user(user_id="12345678")
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.username, "sleeperuser")
        self.assertEqual(user.user_id, "12345678")

    def test_get_user_not_found(self):
        # Mock an exception for a user not found case
        self.client.get.side_effect = SleeperAPIError("User not found")

        with self.assertRaises(SleeperAPIError) as context:
            self.endpoint.get_user(user_id="invalid_id")
        
        self.assertEqual(str(context.exception), "User not found")

    def test_fetch_nfl_leagues(self):
        # Mock a valid user
        mock_user = UserModel(
            username="sleeperuser",
            user_id="12345678",
            display_name="SleeperUser",
            avatar="cc12ec49965eb7856f84d71cf85306af"
        )

        # Mock the API response for the user's leagues
        mock_response = [
            {
                "league_id": "123",
                "name": "Best League",
                "status": "active",
                "sport": "nfl",
                "season": "2023",
                "season_type": "regular",
                "total_rosters": 12,
                "roster_positions": ["QB", "RB", "WR", "TE"],
                "settings": {"playoff_teams": 6},
                "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0}
            }
        ]
        self.client.get.return_value = mock_response

        # Call fetch_nfl_leagues and assert the leagues are correctly added to the user's model
        self.endpoint.fetch_nfl_leagues(user=mock_user, season=2023)
        self.assertEqual(len(mock_user.nfl_leagues), 1)
        league = mock_user.nfl_leagues[0]
        self.assertIsInstance(league, LeagueModel)
        self.assertEqual(league.league_id, "123")
        self.assertEqual(league.name, "Best League")

if __name__ == '__main__':
    unittest.main()
