import unittest
from unittest.mock import MagicMock
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.models.league import LeagueModel
from sleeper_api.exceptions import SleeperAPIError

class TestUserEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = UserEndpoint(self.client)

    def test_fetch_nfl_leagues_success(self):
        # Mock league data response
        mock_league_response = [
            {
                "league_id": "289646328504385536",
                "name": "Sleeperbot Friends League",
                "status": "pre_draft",
                "sport": "nfl",
                "season": "2023",
                "season_type": "regular",
                "total_rosters": 12,
                "roster_positions": ["QB", "RB", "WR", "TE"],
                "settings": {},
                "scoring_settings": {},
                "avatar": "efaefa889ae24046a53265a3c71b8b64",
                "draft_id": "289646328508579840",
                "previous_league_id": "198946952535085056"
            }
        ]
        self.client.get.return_value = mock_league_response

        # Call fetch_nfl_leagues and verify the leagues are correctly fetched
        leagues = self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)
        self.assertEqual(len(leagues), 1)
        league = leagues[0]
        self.assertEqual(league.league_id, "289646328504385536")
        self.assertEqual(league.name, "Sleeperbot Friends League")

    def test_fetch_nfl_leagues_missing_required_field(self):
        # Mock league data response with a missing required field (e.g., 'name')
        mock_league_response = [
            {
                "league_id": "289646328504385536",
                "status": "pre_draft",
                "sport": "nfl",
                "season": "2023",
                "season_type": "regular",
                "total_rosters": 12,
                "roster_positions": ["QB", "RB", "WR", "TE"],
                "settings": {},
                "scoring_settings": {},
                "avatar": "efaefa889ae24046a53265a3c71b8b64",
                "draft_id": "289646328508579840",
                "previous_league_id": "198946952535085056"
            }
        ]
        self.client.get.return_value = mock_league_response

        # Test that missing 'name' raises a TypeError
        with self.assertRaises(TypeError):
            self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)

    def test_fetch_nfl_leagues_no_leagues_found(self):
        # Mock no leagues found case
        self.client.get.return_value = []

        with self.assertRaises(SleeperAPIError) as context:
            self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)

        self.assertEqual(str(context.exception), "No League data found for the 2023 season.")

if __name__ == '__main__':
    unittest.main()
