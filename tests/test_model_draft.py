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

    def test_draft_model_handles_null_draft_order_for_pre_draft_status(self):
        # Regression test for PR #29 review Finding 1 on commit 7306e5a.
        # Sleeper legitimately returns draft_order=null for a 'pre_draft'
        # draft -- the pick order isn't assigned until the draft actually
        # starts -- confirmed against the live API for a real, currently
        # not-yet-conducted 2026-season draft. Treating draft_order as a
        # required field rejected every such draft with a TypeError, which
        # mattered a lot once get_all_drafts()/get_drafts_by_user() started
        # defaulting to the upcoming (and therefore often not-yet-drafted)
        # season during preseason.
        realistic_pending_draft_payload = {
            "draft_id": "1389688714547974145",
            "league_id": "1389688714547974144",
            "season": "2026",
            "season_type": "regular",
            "status": "pre_draft",
            "draft_order": None,
            "sport": "nfl",
            "type": "snake",
            "start_time": None,
            "created": 1785690118017,
        }

        draft = DraftModel.from_json(realistic_pending_draft_payload)

        self.assertEqual(draft.draft_id, "1389688714547974145")
        self.assertEqual(draft.status, "pre_draft")
        self.assertEqual(draft.draft_order, {})  # coerced from None, not raised

    def test_draft_model_invalid_data(self):
        # Provide invalid draft data with missing required fields
        draft_data = {
            "draft_id": "12345"  # Missing required fields: league_id, season, status
        }

        # Since we're expecting missing required fields to raise an error,
        # TypeError will be raised for missing arguments during initialization
        with self.assertRaises(TypeError):
            DraftModel.from_json(draft_data)

    def test_draft_model_constructor_requires_arguments(self):
        # Regression test: adding Optional[...] annotations to satisfy mypy
        # must not make the constructor's arguments callable with no
        # arguments -- DraftModel() should still raise TypeError, not
        # silently succeed with draft_id/league_id coerced to the string
        # "None".
        with self.assertRaises(TypeError):
            DraftModel()

if __name__ == '__main__':
    unittest.main()
