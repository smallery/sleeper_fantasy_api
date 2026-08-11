import unittest
from unittest.mock import MagicMock, patch
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.models.league import LeagueModel
from sleeper_api.models.user import UserModel
from sleeper_api.exceptions import SleeperAPIError, UserNotFoundError

class TestUserEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = UserEndpoint(self.client)
        # fetch_nfl_leagues/get_all_drafts resolve the current season (for
        # the upper-bound check / the default) via get_current_season(),
        # which itself calls client.get("state/nfl"). Patching it directly
        # keeps these tests about league/draft behavior, not season
        # resolution (that has its own coverage in test_config.py), and
        # avoids the plain MagicMock client returning mismatched shapes for
        # whichever call happens to hit the state endpoint.
        patcher = patch(
            "sleeper_api.endpoints.user_endpoint.get_current_season", return_value=2025
        )
        self.mock_get_current_season = patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_user_by_username_success(self):
        self.client.get.return_value = {
            "username": "sleeperuser",
            "user_id": "12345678",
            "display_name": "SleeperUser",
            "avatar": "cc12ec49965eb7856f84d71cf85306af",
        }

        user = self.endpoint.get_user(username="sleeperuser")
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.user_id, "12345678")

    def test_get_user_unknown_username_raises_user_not_found_error(self):
        # SleeperClient._handle_response() returns None on 404 -- get_user()
        # is the endpoint method that turns that into a raise, since a
        # missing user was looked up by name, not an optional resource
        # (see issue #17).
        self.client.get.return_value = None

        with self.assertRaises(UserNotFoundError) as context:
            self.endpoint.get_user(username="definitely-not-real-zzzz")

        self.assertEqual(context.exception.username, "definitely-not-real-zzzz")

    def test_get_user_neither_id_nor_username_raises_sleeper_api_error(self):
        with self.assertRaises(SleeperAPIError):
            self.endpoint.get_user()

    def test_fetch_nfl_leagues_success(self):
        # Mock league data response
        mock_league_response = [
            {
                "league_id": "289646328504385536",
                "name": "Sleeperbot Friends League",
                "status": "pre_draft",
                "sport": "nfl",
                "season": "2023",
                "season_type": "regular",
                "total_rosters": 12,
                "roster_positions": ["QB", "RB", "WR", "TE"],
                "settings": {},
                "scoring_settings": {},
                "avatar": "efaefa889ae24046a53265a3c71b8b64",
                "draft_id": "289646328508579840",
                "previous_league_id": "198946952535085056"
            }
        ]
        self.client.get.return_value = mock_league_response

        # Call fetch_nfl_leagues and verify the leagues are correctly fetched
        leagues = self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)
        self.assertEqual(len(leagues), 1)
        league = leagues[0]
        self.assertEqual(league.league_id, "289646328504385536")
        self.assertEqual(league.name, "Sleeperbot Friends League")

    def test_fetch_nfl_leagues_missing_required_field(self):
        # Mock league data response with a missing required field (e.g., 'name')
        mock_league_response = [
            {
                "league_id": "289646328504385536",
                "status": "pre_draft",
                "sport": "nfl",
                "season": "2023",
                "season_type": "regular",
                "total_rosters": 12,
                "roster_positions": ["QB", "RB", "WR", "TE"],
                "settings": {},
                "scoring_settings": {},
                "avatar": "efaefa889ae24046a53265a3c71b8b64",
                "draft_id": "289646328508579840",
                "previous_league_id": "198946952535085056"
            }
        ]
        self.client.get.return_value = mock_league_response

        # Test that missing 'name' raises a TypeError
        with self.assertRaises(TypeError):
            self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)

    def test_fetch_nfl_leagues_no_leagues_found_returns_empty_list(self):
        # A user simply having no leagues in a season is a normal outcome,
        # not an error -- fetch_nfl_leagues used to raise SleeperAPIError
        # here, which collided badly with issue #18 (the wrong default
        # season made this fire routinely). See issue #21.
        self.client.get.return_value = []

        leagues = self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2023)
        self.assertEqual(leagues, [])

    def test_fetch_nfl_leagues_uses_current_season_by_default(self):
        self.client.get.return_value = []
        self.endpoint.fetch_nfl_leagues(user_id="12345678")
        self.client.get.assert_called_with("user/12345678/leagues/nfl/2025")

    def test_fetch_nfl_leagues_future_season_raises(self):
        with self.assertRaises(SleeperAPIError):
            self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2099)

    def test_fetch_nfl_leagues_accepts_explicit_reported_preseason_season(self):
        # Regression test for PR #29 review Finding 1: during preseason,
        # /state/nfl reports the *upcoming* season (e.g. 2026) while
        # get_current_season()'s default steps back to 2025 (the season with
        # data). The upper-bound check must still accept an explicit
        # season=2026 -- that's a real season Sleeper reports and leagues for
        # it can already exist -- rather than rejecting it before the
        # leagues endpoint is even queried.
        def fake_get_current_season(client, prefer_previous_during_preseason=True):
            return 2025 if prefer_previous_during_preseason else 2026

        self.mock_get_current_season.side_effect = fake_get_current_season
        self.client.get.return_value = []

        # Must not raise.
        self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2026)
        self.client.get.assert_called_with("user/12345678/leagues/nfl/2026")

    def test_fetch_nfl_leagues_still_rejects_season_beyond_reported(self):
        # The bound isn't removed, just corrected to the unadjusted value --
        # a season further out than what /state/nfl reports is still invalid.
        def fake_get_current_season(client, prefer_previous_during_preseason=True):
            return 2025 if prefer_previous_during_preseason else 2026

        self.mock_get_current_season.side_effect = fake_get_current_season
        with self.assertRaises(SleeperAPIError):
            self.endpoint.fetch_nfl_leagues(user_id="12345678", season=2027)

    def test_get_all_drafts_uses_current_season_by_default(self):
        self.client.get.return_value = []
        with self.assertRaises(SleeperAPIError):
            # Empty result still raises here -- get_all_drafts' empty-result
            # behavior is unchanged by this batch (only fetch_nfl_leagues's
            # was in scope for issue #21). This test is about the season
            # defaulting through to the request URL.
            self.endpoint.get_all_drafts(user_id="12345678")
        self.client.get.assert_called_with("user/12345678/drafts/nfl/2025")
        # Drafts must resolve "current season" to the upcoming one during
        # preseason, not the previous one (see PR #29 review, Finding 2).
        self.mock_get_current_season.assert_called_once_with(
            self.client, prefer_previous_during_preseason=False
        )

    def test_get_all_drafts_explicit_season_skips_resolution(self):
        self.client.get.return_value = []
        with self.assertRaises(SleeperAPIError):
            self.endpoint.get_all_drafts(user_id="12345678", season=2019)
        self.client.get.assert_called_with("user/12345678/drafts/nfl/2019")

    def test_get_all_drafts_defaults_to_upcoming_season_during_preseason(self):
        # Regression test for PR #29 review Finding 2: a previous
        # implementation stepped back to the previous season here during
        # preseason, silently returning last year's (real, existing) drafts
        # instead of this season's -- a wrong answer that looks valid because
        # last season's drafts genuinely exist. Drafts for the upcoming
        # season happen *during* preseason, so "current season" for a draft
        # lookup must mean the upcoming one.
        def fake_get_current_season(client, prefer_previous_during_preseason=True):
            return 2025 if prefer_previous_during_preseason else 2026

        self.mock_get_current_season.side_effect = fake_get_current_season
        self.client.get.return_value = []
        with self.assertRaises(SleeperAPIError):
            self.endpoint.get_all_drafts(user_id="12345678")
        self.client.get.assert_called_with("user/12345678/drafts/nfl/2026")

    def test_get_all_drafts_converts_not_yet_conducted_drafts_during_preseason(self):
        # Regression test for PR #29 review Finding 1 on commit 7306e5a:
        # defaulting to the upcoming season during preseason (Finding 2) is
        # only a real fix if the upcoming season's drafts can actually be
        # converted -- they haven't been conducted yet, so Sleeper returns
        # draft_order=null, which DraftModel.from_json() used to reject as a
        # missing required field. That turned "wrong season" into "no
        # results at all", which is not an improvement. This exercises the
        # full get_all_drafts() -> get_draft_by_id() -> DraftModel.from_json()
        # chain end to end with a realistic 'pre_draft' payload.
        pending_draft_list_entry = {
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
        pending_draft_full = dict(pending_draft_list_entry)  # draft/{id} shape used by get_draft_by_id

        def fake_get(endpoint, params=None):
            if endpoint == "user/12345678/drafts/nfl/2026":
                return [pending_draft_list_entry]
            if endpoint == f"draft/{pending_draft_list_entry['draft_id']}":
                return pending_draft_full
            raise AssertionError(f"unexpected endpoint: {endpoint}")

        self.mock_get_current_season.side_effect = (
            lambda client, prefer_previous_during_preseason=True: 2026
        )
        self.client.get.side_effect = fake_get

        drafts = self.endpoint.get_all_drafts(user_id="12345678")

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].draft_id, "1389688714547974145")
        self.assertEqual(drafts[0].status, "pre_draft")
        # draft_order=null converts to an empty dict rather than raising.
        self.assertEqual(drafts[0].draft_order, {})


if __name__ == '__main__':
    unittest.main()
