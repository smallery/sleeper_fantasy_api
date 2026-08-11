import unittest
from unittest.mock import MagicMock, patch
from sleeper_api.endpoints.draft_endpoint import DraftEndpoint
from sleeper_api.exceptions import SleeperAPIError
from sleeper_api.models.draft import DraftModel
from sleeper_api.models.picks import PicksModel
from sleeper_api.models.traded_picks import TradedPickModel


class TestDraftEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = DraftEndpoint(self.client)

    def test_get_drafts_by_user_uses_current_season_by_default(self):
        # season now defaults to None and is resolved via get_current_season()
        # against GET /state/nfl instead of the frozen-at-import DEFAULT_SEASON
        # constant (see issue #18).
        with patch(
            "sleeper_api.endpoints.draft_endpoint.get_current_season", return_value=2025
        ) as mock_get_current_season:
            self.client.get.return_value = []
            self.endpoint.get_drafts_by_user(user_id="12345678")
            # Drafts must resolve to the *upcoming* season during preseason,
            # not the previous one (see PR #29 review, Finding 2) -- a
            # season's draft happens during that season's own preseason
            # window, so defaulting to last season would silently return the
            # wrong (but plausible-looking) drafts.
            mock_get_current_season.assert_called_once_with(
                self.client, prefer_previous_during_preseason=False
            )
            self.client.get.assert_called_with("user/12345678/drafts/nfl/2025")

    def test_get_drafts_by_user_defaults_to_upcoming_season_during_preseason(self):
        # Regression test for PR #29 review Finding 2: during preseason,
        # /state/nfl reports the upcoming season (no data yet for most
        # things), but drafts for that upcoming season are exactly what's
        # happening *right now*. A previous implementation stepped back to
        # the previous season here, which silently returned last year's
        # (real, existing) drafts instead -- a wrong answer that looks valid.
        def fake_get_current_season(client, prefer_previous_during_preseason=True):
            return 2025 if prefer_previous_during_preseason else 2026

        with patch(
            "sleeper_api.endpoints.draft_endpoint.get_current_season",
            side_effect=fake_get_current_season,
        ):
            self.client.get.return_value = []
            self.endpoint.get_drafts_by_user(user_id="12345678")
            self.client.get.assert_called_with("user/12345678/drafts/nfl/2026")

    def test_get_drafts_by_user_converts_not_yet_conducted_drafts_during_preseason(self):
        # Regression test for PR #29 review Finding 1 on commit 7306e5a:
        # defaulting to the upcoming season during preseason (Finding 2) is
        # only a real fix if the upcoming season's drafts can actually be
        # converted -- they haven't been conducted yet, so Sleeper returns
        # draft_order=null, which DraftModel.from_json() used to reject as a
        # missing required field. That turned "wrong season" into "no
        # results at all". Exercises the full get_drafts_by_user() ->
        # get_draft_by_id() -> DraftModel.from_json() chain end to end with
        # a realistic 'pre_draft' payload.
        pending_draft = {
            "draft_id": "1389688714547974145",
            "league_id": "1389688714547974144",
            "season": "2026",
            "season_type": "regular",
            "status": "pre_draft",
            "draft_order": None,
            "sport": "nfl",
            "type": "snake",
            "start_time": None,
        }

        def fake_get(endpoint, params=None):
            if endpoint == "user/12345678/drafts/nfl/2026":
                return [pending_draft]
            if endpoint == f"draft/{pending_draft['draft_id']}":
                return pending_draft
            raise AssertionError(f"unexpected endpoint: {endpoint}")

        with patch(
            "sleeper_api.endpoints.draft_endpoint.get_current_season",
            side_effect=lambda client, prefer_previous_during_preseason=True: 2026,
        ):
            self.client.get.side_effect = fake_get
            drafts = self.endpoint.get_drafts_by_user(user_id="12345678")

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].draft_id, "1389688714547974145")
        self.assertEqual(drafts[0].status, "pre_draft")
        self.assertEqual(drafts[0].draft_order, {})

    def test_get_drafts_by_user_explicit_season_skips_resolution(self):
        with patch(
            "sleeper_api.endpoints.draft_endpoint.get_current_season"
        ) as mock_get_current_season:
            self.client.get.return_value = []
            self.endpoint.get_drafts_by_user(user_id="12345678", season=2019)
            mock_get_current_season.assert_not_called()
            self.client.get.assert_called_with("user/12345678/drafts/nfl/2019")

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
        self.assertIsInstance(draft, DraftModel)
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
        self.assertIsInstance(drafts[0], DraftModel)
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

        # Call the get_draft_picks method
        picks = self.endpoint.get_draft_picks(draft_id="12345")

        # Assert the correct number of picks
        self.assertEqual(len(picks), 1)

        # Assert individual fields
        self.assertEqual(picks[0].player_id, "1408")
        self.assertEqual(picks[0].player_name, "Le'Veon Bell")
        self.assertEqual(picks[0].metadata.team, "PIT")
        self.assertEqual(picks[0].metadata.position, "RB")


    def test_get_traded_picks_success(self):
        # Mock traded picks data
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
        
        self.assertEqual(len(traded_picks), 2)
        self.assertIsInstance(traded_picks[0], TradedPickModel)
        self.assertEqual(traded_picks[0].season, "2022")
        self.assertEqual(traded_picks[0].round, 1)
        self.assertEqual(traded_picks[0].owner_id, 3)

        
if __name__ == '__main__':
    unittest.main()
