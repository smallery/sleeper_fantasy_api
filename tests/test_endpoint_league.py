import unittest
from unittest.mock import MagicMock
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.models.league import LeagueModel
from sleeper_api.models.roster import RosterModel
from sleeper_api.exceptions import SleeperAPIError

class TestLeagueEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = LeagueEndpoint(self.client)

    def test_get_league_with_invalid_id(self):
        # Mock the client to raise an exception for an invalid league ID
        self.client.get.side_effect = SleeperAPIError("League not found")

        with self.assertRaises(SleeperAPIError) as context:
            self.endpoint.get_league(league_id="invalid_league")
        
        self.assertEqual(str(context.exception), "League not found")

    def test_get_league_empty_response(self):
        # Mock the client to return an empty response
        self.client.get.return_value = None

        with self.assertRaises(SleeperAPIError, msg="League not found"):
            self.endpoint.get_league(league_id="empty_league")

    def test_get_league_success(self):
        # Mock a valid league response
        mock_league_response = {
            "league_id": "123",
            "name": "Test League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 10,
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {"playoff_teams": 4},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0}
        }

        # Mock the get request to return the league data
        self.client.get.return_value = mock_league_response

        # Call the get_league method and assert the response is correct
        league = self.endpoint.get_league(league_id="123")
        self.assertIsInstance(league, LeagueModel)
        self.assertEqual(league.league_id, "123")
        self.assertEqual(league.name, "Test League")
        self.assertEqual(league.sport, "nfl")
        self.assertEqual(league.season, "2023")

    def test_fetch_rosters(self):
        # Mock roster data response
        mock_response = [
            {
                "starters": ["123", "456"],
                "settings": {"wins": 5, "losses": 2},
                "roster_id": 1,
                "reserve": ["789"],
                "players": ["123", "456", "789"],
                "owner_id": "owner123",
                "league_id": "league123"
            }
        ]
        self.client.get.return_value = mock_response

        # Call get_rosters and assert the response is correct
        rosters = self.endpoint.get_rosters(league_id="123")
        self.assertEqual(len(rosters), 1)
        self.assertIsInstance(rosters[0], RosterModel)
        self.assertEqual(rosters[0].roster_id, 1)
        self.assertEqual(rosters[0].players, ["123", "456", "789"])
        self.assertEqual(rosters[0].owner_id, "owner123")
        self.assertEqual(rosters[0].starters, ["123", "456"])

if __name__ == '__main__':
    unittest.main()
