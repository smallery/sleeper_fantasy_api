import unittest
import time
from sleeper_api.models.picks import PicksModel, PickMetadata

class TestPerformance(unittest.TestCase):

    def test_large_data_handling(self):
        # Simulate a large number of pick objects
        large_data = [{
            "player_id": str(i),
            "picked_by": str(i),
            "roster_id": str(i),
            "round": 5,
            "draft_slot": 6,
            "pick_no": i,
            "metadata": {
                "team": "PIT",
                "status": "Active",
                "sport": "nfl",
                "position": "RB",
                "player_id": str(i),
                "number": "26",
                "news_updated": "1515698101257",
                "last_name": "Bell",
                "injury_status": "",
                "first_name": "Le'Veon"
            },
            "is_keeper": None,
            "draft_id": str(i)
        } for i in range(10000)]

        start_time = time.time()
        picks_model = PicksModel.from_list(large_data)  # Now using the from_list method
        duration = time.time() - start_time

        self.assertTrue(duration < 2)  # Ensure the operation is under 2 seconds
        self.assertEqual(len(picks_model), 10000)  # Test the number of picks

if __name__ == '__main__':
    unittest.main()
