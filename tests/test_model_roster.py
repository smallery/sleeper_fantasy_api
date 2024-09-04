import unittest
from sleeper_api.models.roster import RosterModel

class TestRosterModel(unittest.TestCase):

    def setUp(self):
        self.valid_roster_data = {
            "starters": ["2307", "2257", "4034", "147", "642", "4039", "515", "4149", "DET"],
            "settings": {
                "wins": 5,
                "waiver_position": 7,
                "waiver_budget_used": 0,
                "total_moves": 0,
                "ties": 0,
                "losses": 9,
                "fpts_decimal": 78,
                "fpts_against_decimal": 32,
                "fpts_against": 1670,
                "fpts": 1617
            },
            "roster_id": 1,
            "reserve": [],
            "players": ["1046", "138", "147", "2257", "2307", "2319", "4034", "4039", "4040", "4149", "421", "515", "642", "745", "DET"],
            "owner_id": "188815879448829952",
            "league_id": "206827432160788480"
        }

    def test_roster_model_initialization(self):
        # Test valid initialization
        roster = RosterModel.from_dict(self.valid_roster_data)

        self.assertEqual(len(roster.starters), 9)
        self.assertEqual(len(roster.players), 15)
        self.assertEqual(roster.roster_id, 1)
        self.assertEqual(roster.owner_id, "188815879448829952")
        self.assertEqual(roster.league_id, "206827432160788480")
        self.assertEqual(roster.settings['wins'], 5)

    def test_roster_model_to_dict(self):
        # Test conversion back to dict
        roster = RosterModel.from_dict(self.valid_roster_data)
        roster_dict = roster.to_dict()

        self.assertEqual(roster_dict['starters'], self.valid_roster_data['starters'])
        self.assertEqual(roster_dict['players'], self.valid_roster_data['players'])
        self.assertEqual(roster_dict['roster_id'], self.valid_roster_data['roster_id'])
        self.assertEqual(roster_dict['owner_id'], self.valid_roster_data['owner_id'])
        self.assertEqual(roster_dict['league_id'], self.valid_roster_data['league_id'])

    def test_roster_model_invalid_data_types(self):
        # Test invalid data types
        invalid_data = self.valid_roster_data.copy()
        invalid_data['roster_id'] = 'invalid_id'  # Should be an int

        with self.assertRaises(ValueError):
            RosterModel.from_dict(invalid_data)

        invalid_data = self.valid_roster_data.copy()
        invalid_data['starters'] = [2307, 2257]  # Should be List[str]

        with self.assertRaises(ValueError):
            RosterModel.from_dict(invalid_data)

        invalid_data = self.valid_roster_data.copy()
        invalid_data['settings'] = []  # Should be Dict

        with self.assertRaises(ValueError):
            RosterModel.from_dict(invalid_data)

    def test_roster_model_missing_fields(self):
        # Test missing fields
        invalid_data = self.valid_roster_data.copy()
        del invalid_data['starters']

        with self.assertRaises(KeyError):
            RosterModel.from_dict(invalid_data)

    def test_roster_model_repr(self):
        # Test __repr__ method
        roster = RosterModel.from_dict(self.valid_roster_data)
        expected_repr = "<RosterModel(roster_id=1, owner_id=188815879448829952, league_id=206827432160788480)>"
        self.assertEqual(repr(roster), expected_repr)

if __name__ == '__main__':
    unittest.main()
