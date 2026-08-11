"""Tests for current-season resolution (see GitHub issue #18)."""
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sleeper_api import config
from sleeper_api.exceptions import SleeperAPIError


class TestClockEstimateSeason(unittest.TestCase):
    """
    Coverage for the wall-clock fallback only -- this path is meant to be a
    last resort when /state/nfl is unreachable, not the normal path (that's
    exactly the bug issue #18 reported: DEFAULT_SEASON always used the
    clock). Pinned to January, June, and November per the issue's acceptance
    criteria, since an NFL season is labelled by the year it starts and the
    boundary is the September rollover.
    """

    def test_january_belongs_to_previous_septembers_season(self):
        self.assertEqual(config._clock_estimate_season(datetime(2026, 1, 15)), 2025)

    def test_june_belongs_to_previous_septembers_season(self):
        self.assertEqual(config._clock_estimate_season(datetime(2026, 6, 1)), 2025)

    def test_november_belongs_to_this_septembers_season(self):
        self.assertEqual(config._clock_estimate_season(datetime(2026, 11, 1)), 2026)

    def test_september_itself_belongs_to_the_new_season(self):
        # The rollover boundary itself -- games for the new season start in
        # September, so the 1st already belongs to the new season.
        self.assertEqual(config._clock_estimate_season(datetime(2026, 9, 1)), 2026)

    def test_august_still_belongs_to_the_previous_season(self):
        self.assertEqual(config._clock_estimate_season(datetime(2026, 8, 31)), 2025)


class TestGetCurrentSeason(unittest.TestCase):
    """
    get_current_season() is the fix itself: it asks GET /state/nfl instead
    of trusting the clock, resolves per call (subject to a short cache)
    instead of freezing at import, and documents the preseason ambiguity
    (issue #18's "design question") via an explicit flag.
    """

    def setUp(self):
        # The cache is process-wide module state; without clearing it here,
        # whichever test runs first would poison every test that follows for
        # up to _SEASON_CACHE_TTL_SECONDS.
        config._season_cache.clear()
        self.client = MagicMock()

    def _state(self, season="2025", season_type="regular"):
        return {"season": season, "week": 1, "season_type": season_type, "display_week": 1}

    def test_regular_season_returns_reported_season(self):
        self.client.get.return_value = self._state(season_type="regular")
        self.assertEqual(config.get_current_season(self.client), 2025)

    def test_preseason_defaults_to_previous_season(self):
        # The upcoming season /state/nfl reports during "pre" has no
        # projections/leagues/etc. yet -- "the season with data" is last
        # season, which is the default callers get unless they opt out.
        self.client.get.return_value = self._state(season="2026", season_type="pre")
        self.assertEqual(config.get_current_season(self.client), 2025)

    def test_preseason_returns_reported_season_when_opted_out(self):
        self.client.get.return_value = self._state(season="2026", season_type="pre")
        self.assertEqual(
            config.get_current_season(self.client, prefer_previous_during_preseason=False),
            2026,
        )

    def test_postseason_and_off_are_not_treated_as_preseason(self):
        for season_type in ("post", "off", "regular"):
            with self.subTest(season_type=season_type):
                config._season_cache.clear()
                self.client.get.return_value = self._state(season="2025", season_type=season_type)
                self.assertEqual(config.get_current_season(self.client), 2025)

    @patch("sleeper_api.config._clock_estimate_season", return_value=1999)
    def test_falls_back_to_clock_estimate_when_state_endpoint_unreachable(self, mock_estimate):
        self.client.get.side_effect = SleeperAPIError("boom")
        with self.assertLogs("sleeper_api.config", level="WARNING") as logs:
            result = config.get_current_season(self.client)
        self.assertEqual(result, 1999)
        self.assertTrue(any("state/nfl" in entry for entry in logs.output))

    def test_falls_back_when_response_is_missing_season_key(self):
        # Malformed/unexpected payload shape should degrade the same way an
        # unreachable endpoint does, not raise out of a "default season" call.
        self.client.get.return_value = {"unexpected": "shape"}
        with self.assertLogs("sleeper_api.config", level="WARNING"):
            result = config.get_current_season(self.client)
        self.assertIsInstance(result, int)

    def test_repeated_calls_within_ttl_hit_the_cache_once(self):
        self.client.get.return_value = self._state()
        config.get_current_season(self.client)
        config.get_current_season(self.client)
        config.get_current_season(self.client)
        self.client.get.assert_called_once_with("state/nfl")

    def test_cache_cleared_triggers_a_fresh_request(self):
        self.client.get.return_value = self._state()
        config.get_current_season(self.client)
        config._season_cache.clear()
        config.get_current_season(self.client)
        self.assertEqual(self.client.get.call_count, 2)

    def test_process_does_not_freeze_on_first_resolved_value(self):
        # This is the "frozen at import" half of issue #18: unlike the old
        # DEFAULT_SEASON module constant, a stale cache entry is not
        # permanent -- once it's invalidated, the *new* /state/nfl response
        # wins on the very next call, in the same process.
        self.client.get.return_value = self._state(season="2025")
        self.assertEqual(config.get_current_season(self.client), 2025)

        config._season_cache.clear()
        self.client.get.return_value = self._state(season="2026")
        self.assertEqual(config.get_current_season(self.client), 2026)


if __name__ == '__main__':
    unittest.main()
