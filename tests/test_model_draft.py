import unittest
from sleeper_api.models.draft import DraftModel

class TestDraftModel(unittest.TestCase):

    def test_draft_model_initialization(self):
        # Provide mock draft data
        draft_data = {
            "draft_id": "12345",
            "league_id": "54321",
            "season": "2022",
            "status": "complete",
            "draft_order": {1: "team1", 2: "team2"},
            "picks": [{"round": 1, "pick": 1, "team_id": "team1"}]
        }

        # Initialize the draft model using from_json
        draft = DraftModel.from_json(draft_data)

        # Test attribute assignments
        self.assertEqual(draft.draft_id, "12345")
        self.assertEqual(draft.league_id, "54321")
        self.assertEqual(draft.season, "2022")
        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.draft_order, {1: "team1", 2: "team2"})
        self.assertEqual(draft.picks, [{"round": 1, "pick": 1, "team_id": "team1"}])

    def test_draft_model_missing_optional_fields(self):
        # Provide mock draft data without optional fields like picks
        draft_data = {
            "draft_id": "12345",
            "league_id": "54321",
            "season": "2022",
            "status": "complete",
            "draft_order": {1: "team1", 2: "team2"}
        }

        # Initialize the draft model using from_json
        draft = DraftModel.from_json(draft_data)

        # Test that picks default to an empty list when missing
        self.assertEqual(draft.draft_id, "12345")
        self.assertEqual(draft.league_id, "54321")
        self.assertEqual(draft.season, "2022")
        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.draft_order, {1: "team1", 2: "team2"})
        self.assertEqual(draft.picks, [])  # Ensure default empty list for picks

    def test_draft_model_invalid_data(self):
        # Provide invalid draft data with missing required fields
        draft_data = {
            "draft_id": "12345"  # Missing required fields: league_id, season, status
        }

        # Since we're expecting missing required fields to raise an error,
        # TypeError will be raised for missing arguments during initialization
        with self.assertRaises(TypeError):
            DraftModel.from_json(draft_data)

if __name__ == '__main__':
    unittest.main()
