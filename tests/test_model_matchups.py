import unittest
from sleeper_api.models.matchups import MatchupModel

class TestMatchupModel(unittest.TestCase):

    def test_matchup_model_initialization(self):
        # Mock matchup data
        matchup_data = {
            "starters": ["421", "4035", "3242", "2133", "2449", "4531", "2257", "788", "PHI"],
            "roster_id": 1,
            "players": ["1352", "1387", "2118", "2133", "2182", "223", "2319", "2449", "3208", "4035", "421", "4881", "4892", "788", "CLE"],
            "matchup_id": 2,
            "points": 120.5,
            "custom_points": None
        }

        # Initialize the MatchupModel
        matchup = MatchupModel.from_dict(matchup_data)

        # Test that all attributes are assigned correctly
        self.assertEqual(matchup.starters, ["421", "4035", "3242", "2133", "2449", "4531", "2257", "788", "PHI"])
        self.assertEqual(matchup.roster_id, 1)
        self.assertEqual(matchup.players, ["1352", "1387", "2118", "2133", "2182", "223", "2319", "2449", "3208", "4035", "421", "4881", "4892", "788", "CLE"])
        self.assertEqual(matchup.matchup_id, 2)
        self.assertEqual(matchup.points, 120.5)
        self.assertIsNone(matchup.custom_points)  # custom_points is None

    def test_matchup_model_serialization(self):
        # Mock matchup data
        matchup_data = {
            "starters": ["421", "4035", "3242", "2133", "2449", "4531", "2257", "788", "PHI"],
            "roster_id": 1,
            "players": ["1352", "1387", "2118", "2133", "2182", "223", "2319", "2449", "3208", "4035", "421", "4881", "4892", "788", "CLE"],
            "matchup_id": 2,
            "points": 120.5,
            "custom_points": None
        }

        # Initialize the MatchupModel
        matchup = MatchupModel.from_dict(matchup_data)

        # Serialize the MatchupModel back to a dictionary
        serialized_data = matchup.to_dict()

        # Ensure the serialized data matches the original data
        self.assertEqual(serialized_data, matchup_data)

    def test_matchup_model_missing_optional_fields(self):
        # Mock matchup data without custom_points
        matchup_data = {
            "starters": ["421", "4035", "3242", "2133", "2449", "4531", "2257", "788", "PHI"],
            "roster_id": 1,
            "players": ["1352", "1387", "2118", "2133", "2182", "223", "2319", "2449", "3208", "4035", "421", "4881", "4892", "788", "CLE"],
            "matchup_id": 2,
            "points": 120.5
        }

        # Initialize the MatchupModel
        matchup = MatchupModel.from_dict(matchup_data)

        # Ensure optional fields are handled correctly
        self.assertEqual(matchup.custom_points, None)

    def test_matchup_model_invalid_data(self):
        # Test invalid data types
        invalid_matchup_data = {
            "starters": "421, 4035, 3242",  # starters should be a list, not a string
            "roster_id": "1",  # roster_id should be an int, not a string
            "players": ["1352", "1387", "2118"],
            "matchup_id": 2,
            "points": "120.5"  # points should be a float, not a string
        }

        # Ensure it raises a TypeError or ValueError due to invalid types
        with self.assertRaises(TypeError):
            MatchupModel.from_dict(invalid_matchup_data)

if __name__ == '__main__':
    unittest.main()
