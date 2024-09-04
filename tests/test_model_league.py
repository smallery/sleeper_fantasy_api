import unittest
from sleeper_api.models.league import LeagueModel

class TestLeagueModel(unittest.TestCase):

    def test_league_model_initialization(self):
        # Mock league data
        league_data = {
            "league_id": "123456",
            "name": "Test League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 12,
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {"playoff_teams": 6},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0},
            "metadata": {"scoring_type": "PPR"},
            "avatar": "avatar123",
            "draft_id": "draft123",
            "bracket_id": 1,
            "loser_bracket_id": 2,
            "group_id": "group1",
            "last_message_id": "msg123",
            "last_author_id": "user123",
            "last_author_display_name": "Test User",
            "last_author_avatar": "avatar456",
            "last_message_time": 1629292929292,
            "last_transaction_id": "txn123",
            "previous_league_id": "prev_league123"
        }

        league = LeagueModel.from_json(league_data)

        self.assertEqual(league.league_id, "123456")
        self.assertEqual(league.name, "Test League")
        self.assertEqual(league.status, "active")
        self.assertEqual(league.sport, "nfl")
        self.assertEqual(league.season, "2023")
        self.assertEqual(league.season_type, "regular")
        self.assertEqual(league.total_rosters, 12)
        self.assertEqual(league.roster_positions, ["QB", "RB", "WR", "TE"])
        self.assertEqual(league.settings, {"playoff_teams": 6})
        self.assertEqual(league.scoring_settings, {"pass_td": 4.0, "rush_td": 6.0})
        self.assertEqual(league.metadata, {"scoring_type": "PPR"})
        self.assertEqual(league.avatar, "avatar123")
        self.assertEqual(league.draft_id, "draft123")
        self.assertEqual(league.bracket_id, 1)
        self.assertEqual(league.loser_bracket_id, 2)
        self.assertEqual(league.group_id, "group1")
        self.assertEqual(league.last_message_id, "msg123")
        self.assertEqual(league.last_author_id, "user123")
        self.assertEqual(league.last_author_display_name, "Test User")
        self.assertEqual(league.last_author_avatar, "avatar456")
        self.assertEqual(league.last_message_time, 1629292929292)
        self.assertEqual(league.last_transaction_id, "txn123")
        self.assertEqual(league.previous_league_id, "prev_league123")

    def test_league_model_missing_optional_fields(self):
        # Test league model with missing optional fields
        league_data = {
            "league_id": "123456",
            "name": "Test League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 12,
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {"playoff_teams": 6},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0}
        }

        league = LeagueModel.from_json(league_data)

        self.assertEqual(league.metadata, {})  # Expect an empty dict instead of None
        self.assertIsNone(league.avatar)
        self.assertIsNone(league.draft_id)
        self.assertIsNone(league.bracket_id)
        self.assertIsNone(league.loser_bracket_id)
        self.assertIsNone(league.group_id)
        self.assertIsNone(league.last_message_id)
        self.assertIsNone(league.last_author_id)
        self.assertIsNone(league.last_author_display_name)
        self.assertIsNone(league.last_author_avatar)
        self.assertIsNone(league.last_message_time)
        self.assertIsNone(league.last_transaction_id)
        self.assertIsNone(league.previous_league_id)


    def test_league_model_to_dict(self):
        # Test converting a LeagueModel to a dictionary
        league_data = {
            "league_id": "123456",
            "name": "Test League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 12,
            "roster_positions": ["QB", "RB", "WR", "TE"],
            "settings": {"playoff_teams": 6},
            "scoring_settings": {"pass_td": 4.0, "rush_td": 6.0},
            "metadata": {"scoring_type": "PPR"}
        }

        league = LeagueModel.from_json(league_data)
        league_dict = league.__dict__

        self.assertEqual(league_dict['league_id'], "123456")
        self.assertEqual(league_dict['name'], "Test League")
        self.assertEqual(league_dict['metadata'], {"scoring_type": "PPR"})
        self.assertEqual(league_dict['settings'], {"playoff_teams": 6})

    def test_league_model_invalid_data(self):
        # Missing required fields (like league_id, name, etc.)
        invalid_league_data = {
            "name": "Test League",
            "status": "active",
            "sport": "nfl",
            "season": "2023",
            "season_type": "regular",
            "total_rosters": 12
            # Missing league_id, roster_positions, settings, and scoring_settings
        }

        with self.assertRaises(TypeError):
            LeagueModel.from_json(invalid_league_data)



if __name__ == '__main__':
    unittest.main()
