import unittest
from unittest.mock import MagicMock
from sleeper_api.endpoints.draft_endpoint import DraftEndpoint
from sleeper_api.exceptions import SleeperAPIError


class TestDraftEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = DraftEndpoint(self.client)

    def test_get_draft_by_id_success(self):
        # Mock draft data
        mock_draft_response = {
            "draft_id": "12345",
            "league_id": "54321",
            "season": "2022",
            "status": "complete",
            "draft_order": {1: "team1", 2: "team2"},
            "picks": [{"round": 1, "pick": 1, "team_id": "team1"}]
        }
        self.client.get.return_value = mock_draft_response

        draft = self.endpoint.get_draft_by_id(draft_id="12345")
        self.assertEqual(draft.draft_id, "12345")
        self.assertEqual(draft.league_id, "54321")
        self.assertEqual(draft.season, "2022")
        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.draft_order[1], "team1")

    def test_get_draft_by_id_not_found(self):
        self.client.get.side_effect = SleeperAPIError("Draft not found")
        with self.assertRaises(SleeperAPIError) as context:
            self.endpoint.get_draft_by_id(draft_id="invalid_id")
        self.assertEqual(str(context.exception), "Draft not found")

    def test_get_drafts_by_league_success(self):
        # Mock multiple drafts response
        mock_drafts_response = [{
            "draft_id": "12345",
            "league_id": "54321",
            "season": "2022",
            "status": "complete",
            "draft_order": {1: "team1", 2: "team2"},
            "picks": [{"round": 1, "pick": 1, "team_id": "team1"}]
        }, {
            "draft_id": "67890",
            "league_id": "54321",
            "season": "2021",
            "status": "complete",
            "draft_order": {1: "team3", 2: "team4"},
            "picks": [{"round": 1, "pick": 1, "team_id": "team3"}]
        }]
        self.client.get.return_value = mock_drafts_response

        drafts = self.endpoint.get_drafts_by_league(league_id="54321")
        self.assertEqual(len(drafts), 2)
        self.assertEqual(drafts[0].draft_id, "12345")
        self.assertEqual(drafts[1].draft_id, "67890")

    def test_get_draft_picks_success(self):
        # Mock picks data
        mock_picks_response = [{
            "player_id": "1408",
            "picked_by": "234343434",
            "roster_id": "1",
            "round": 5,
            "draft_slot": 6,
            "pick_no": 2,
            "metadata": {
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
            },
            "is_keeper": None,
            "draft_id": "257270643320426496"
        }]
        self.client.get.return_value = mock_picks_response

        picks = self.endpoint.get_draft_picks(draft_id="12345")
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0].player_id, "1408")
        self.assertEqual(picks[0].player_name, "Le'Veon Bell")

    def test_get_traded_picks_success(self):
        mock_response = [
            {
                "season": "2022",
                "round": 1,
                "roster_id": 1,
                "previous_owner_id": 2,
                "owner_id": 3
            },
            {
                "season": "2022",
                "round": 2,
                "roster_id": 1,
                "previous_owner_id": 3,
                "owner_id": 4
            }
        ]
        
        self.client.get.return_value = mock_response
        
        traded_picks = self.endpoint.get_traded_picks(draft_id="12345")
        
        self.assertEqual(len(traded_picks.traded_picks), 2)
        self.assertEqual(traded_picks.traded_picks[0].season, "2022")
        self.assertEqual(traded_picks.traded_picks[0].round, 1)
        self.assertEqual(traded_picks.traded_picks[0].owner_id, 3)

        
if __name__ == '__main__':
    unittest.main()
