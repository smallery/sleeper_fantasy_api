import unittest
from sleeper_api.models.picks import PicksModel, PickMetadata
from sleeper_api.exceptions import SleeperAPIError

class TestPicksModel(unittest.TestCase):

    def test_pick_initialization(self):
        metadata = PickMetadata(
            team="PIT",
            status="Active",
            sport="nfl",
            position="RB",
            player_id="1408",
            number="26",
            news_updated="1515698101257",
            last_name="Bell",
            injury_status="",
            first_name="Le'Veon"
        )
        pick = PicksModel(
            player_id="1408",
            picked_by="234343434",
            roster_id="1",
            round=5,
            draft_slot=6,
            pick_no=2,
            metadata=metadata,
            is_keeper=None,
            draft_id="257270643320426496"
        )

        self.assertEqual(pick.player_id, "1408")
        self.assertEqual(pick.player_name, "Le'Veon Bell")
        self.assertEqual(pick.metadata.team, "PIT")

    def test_pick_serialization(self):
        metadata_dict = {
            "team": "PIT",
            "status": "Active",
            "sport": "nfl",
            "position": "RB",
            "player_id": "1408",
            "number": "26",
            "news_updated": "1515698101257",
            "last_name": "Bell",
            "injury_status": "",
            "first_name": "Le'Veon"
        }
        pick_dict = {
            "player_id": "1408",
            "picked_by": "234343434",
            "roster_id": "1",
            "round": 5,
            "draft_slot": 6,
            "pick_no": 2,
            "metadata": metadata_dict,
            "is_keeper": None,
            "draft_id": "257270643320426496"
        }

        pick = PicksModel.from_dict(pick_dict)
        self.assertEqual(pick.to_dict(), pick_dict)

    def test_pick_edge_cases(self):
        # Test initialization with missing or invalid data
        with self.assertRaises(KeyError):
            PickMetadata.from_dict({
                "team": "PIT",
                "sport": "nfl"
                # Missing fields
            })

        # Test invalid types
        with self.assertRaises(SleeperAPIError):
            PicksModel(
                player_id=1408,  # Should be str, not int
                picked_by="234343434",
                roster_id="1",
                round=5,
                draft_slot=6,
                pick_no=2,
                metadata=None,
                is_keeper=None,
                draft_id="257270643320426496"
            )

if __name__ == '__main__':
    unittest.main()
