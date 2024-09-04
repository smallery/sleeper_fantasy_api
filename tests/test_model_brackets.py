import unittest
from sleeper_api.models.brackets import BracketModel

class TestBracketModel(unittest.TestCase):

    def test_bracket_model_initialization(self):
        # Test the initialization of BracketModel with standard data
        bracket_data = {
            "r": 1,
            "m": 1,
            "t1": 3,
            "t2": 6,
            "w": 3,
            "l": 6,
            "t1_from": {"w": 1},
            "t2_from": {"l": 2},
            "p": 1
        }

        bracket = BracketModel.from_dict(bracket_data)

        self.assertEqual(bracket.round, 1)
        self.assertEqual(bracket.match_id, 1)
        self.assertEqual(bracket.team1, 3)
        self.assertEqual(bracket.team2, 6)
        self.assertEqual(bracket.winner, 3)
        self.assertEqual(bracket.loser, 6)
        self.assertEqual(bracket.team1_from, {"w": 1})
        self.assertEqual(bracket.team2_from, {"l": 2})
        self.assertEqual(bracket.position, 1)

    def test_bracket_model_to_dict(self):
        # Test that BracketModel can convert back to a dictionary
        bracket_data = {
            "r": 1,
            "m": 2,
            "t1": {"w": 1},
            "t2": {"l": 1},
            "w": None,
            "l": None,
            "t1_from": {"w": 1},
            "t2_from": {"l": 2},
            "p": 3
        }

        bracket = BracketModel.from_dict(bracket_data)
        bracket_dict = bracket.to_dict()

        self.assertEqual(bracket_dict['r'], 1)
        self.assertEqual(bracket_dict['m'], 2)
        self.assertEqual(bracket_dict['t1'], {"w": 1})
        self.assertEqual(bracket_dict['t2'], {"l": 1})
        self.assertIsNone(bracket_dict['w'])
        self.assertIsNone(bracket_dict['l'])
        self.assertEqual(bracket_dict['t1_from'], {"w": 1})
        self.assertEqual(bracket_dict['t2_from'], {"l": 2})
        self.assertEqual(bracket_dict['p'], 3)

    def test_bracket_model_missing_optional_fields(self):
        # Test the initialization of BracketModel with missing optional fields
        bracket_data = {
            "r": 2,
            "m": 3,
            "t1": 4,
            "t2": 7
        }

        bracket = BracketModel.from_dict(bracket_data)

        self.assertEqual(bracket.round, 2)
        self.assertEqual(bracket.match_id, 3)
        self.assertEqual(bracket.team1, 4)
        self.assertEqual(bracket.team2, 7)
        self.assertIsNone(bracket.winner)
        self.assertIsNone(bracket.loser)
        self.assertIsNone(bracket.team1_from)
        self.assertIsNone(bracket.team2_from)
        self.assertIsNone(bracket.position)

    def test_bracket_model_invalid_data(self):
        # Test the handling of invalid data such as missing required fields
        bracket_data = {
            "m": 3  # Missing required field 'r' (round)
        }

        with self.assertRaises(KeyError):
            BracketModel.from_dict(bracket_data)

if __name__ == '__main__':
    unittest.main()
