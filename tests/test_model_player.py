import unittest
from sleeper_api.models.player import PlayerModel

class TestPlayerModel(unittest.TestCase):

    def test_player_model_initialization(self):
        player_data = {
            "player_id": "1408",
            "first_name": "Le'Veon",
            "last_name": "Bell",
            "position": "RB",
            "team": "PIT",
            "age": 29,
            "status": "Active"
        }

        player = PlayerModel.from_dict(player_data)

        self.assertEqual(player.player_id, "1408")
        self.assertEqual(player.first_name, "Le'Veon")
        self.assertEqual(player.last_name, "Bell")
        self.assertEqual(player.position, "RB")
        self.assertEqual(player.team_abbr, "PIT")  # Using team_abbr logic
        self.assertEqual(player.age, 29)
        self.assertEqual(player.status, "Active")

    def test_player_model_with_missing_data(self):
        # Test case with missing non-essential fields
        player_data = {
            "player_id": "1408",
            "first_name": "Le'Veon",
            "last_name": "Bell",
            "position": "RB",
            "team": "PIT"
        }

        player = PlayerModel.from_dict(player_data)

        self.assertEqual(player.player_id, "1408")
        self.assertEqual(player.first_name, "Le'Veon")
        self.assertEqual(player.last_name, "Bell")
        self.assertEqual(player.position, "RB")
        self.assertEqual(player.team_abbr, "PIT")  # Should use team if team_abbr is None
        self.assertIsNone(player.age)  # Since age is missing, it should be None
        self.assertIsNone(player.status)  # Since status is missing, it should be None

    def test_player_model_with_invalid_data(self):
        # Invalid data types (e.g., age is a string instead of an integer)
        player_data = {
            "player_id": "1408",
            "first_name": "Le'Veon",
            "last_name": "Bell",
            "position": "RB",
            "team": "PIT",
            "age": "twenty-nine"
        }

        # Modify this test based on how you handle type validation in the PlayerModel
        player = PlayerModel.from_dict(player_data)
        
        # Assuming that we don't explicitly raise errors, invalid types might stay as-is
        self.assertEqual(player.age, "twenty-nine")

    def test_player_model_get_attribute(self):
        # Test accessing an arbitrary attribute
        player_data = {
            "player_id": "1408",
            "first_name": "Le'Veon",
            "last_name": "Bell",
            "team": "PIT",
            "college": "Michigan State"
        }

        player = PlayerModel.from_dict(player_data)
        self.assertEqual(player.get_attribute("college"), "Michigan State")
        self.assertIsNone(player.get_attribute("non_existent_key"))  # Non-existent key should return None

if __name__ == '__main__':
    unittest.main()
