"""
Tests for per-client `convert_results` configuration (see GitHub issue #24).

`convert_results` used to be a module-level global (`sleeper_api.config.CONVERT_RESULTS`)
with no supported way to set it once for a client -- every endpoint method took
`convert_results: bool = CONVERT_RESULTS`, overridable only per call. These tests
cover the replacement: `SleeperClient(convert_results=...)` sets a client-level
default that endpoints read via `self.client.convert_results`, with an explicit
per-call argument still winning.
"""
import unittest
from unittest.mock import MagicMock, patch

from sleeper_api.client import SleeperClient
from sleeper_api.config import CONVERT_RESULTS
from sleeper_api.endpoints.draft_endpoint import DraftEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.endpoints.nfl_endpoint import NFLEndpoint
from sleeper_api.endpoints.player_endpoint import PlayerEndpoint
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.models.roster import RosterModel
from sleeper_api.models.user import UserModel


class TestSleeperClientConvertResultsSetting(unittest.TestCase):
    """SleeperClient itself: the constructor argument and its default."""

    def test_default_convert_results_is_true(self):
        client = SleeperClient()
        self.assertTrue(client.convert_results)
        self.assertEqual(client.convert_results, CONVERT_RESULTS)

    def test_convert_results_false_is_stored(self):
        client = SleeperClient(convert_results=False)
        self.assertFalse(client.convert_results)

    def test_convert_results_true_is_stored_explicitly(self):
        client = SleeperClient(convert_results=True)
        self.assertTrue(client.convert_results)


class TestEndpointsReadClientConvertResultsDefault(unittest.TestCase):
    """
    Endpoint methods must resolve an omitted convert_results from
    self.client.convert_results, not a frozen module import -- this is the
    behavior a module-level global could never provide (no "set once").
    """

    ROSTER_JSON = [{
        "roster_id": 1, "owner_id": "u1", "league_id": "l1",
        "players": [], "starters": [], "settings": {}, "reserve": [],
    }]

    USER_JSON = {
        "user_id": "u1", "username": "someone", "display_name": "someone",
        "avatar": None,
    }

    def _mock_client(self, convert_results):
        client = MagicMock()
        client.convert_results = convert_results
        return client

    def test_league_endpoint_true_client_default_converts(self):
        client = self._mock_client(True)
        client.get.return_value = self.ROSTER_JSON
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1")

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], RosterModel)

    def test_league_endpoint_false_client_default_returns_raw(self):
        client = self._mock_client(False)
        client.get.return_value = self.ROSTER_JSON
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1")

        self.assertEqual(result, self.ROSTER_JSON)
        self.assertNotIsInstance(result[0], RosterModel)

    def test_per_call_override_wins_over_true_client_default(self):
        # Client default says "convert", but this one call asks for raw JSON.
        client = self._mock_client(True)
        client.get.return_value = self.ROSTER_JSON
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1", convert_results=False)

        self.assertEqual(result, self.ROSTER_JSON)

    def test_per_call_override_wins_over_false_client_default(self):
        # Client default says "raw", but this one call asks for models.
        client = self._mock_client(False)
        client.get.return_value = self.ROSTER_JSON
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1", convert_results=True)

        self.assertIsInstance(result[0], RosterModel)

    def test_user_endpoint_honors_false_client_default(self):
        client = self._mock_client(False)
        client.get.return_value = self.USER_JSON
        endpoint = UserEndpoint(client)

        result = endpoint.get_user(user_id="u1")

        self.assertEqual(result, self.USER_JSON)
        self.assertNotIsInstance(result, UserModel)

    def test_user_endpoint_honors_true_client_default(self):
        client = self._mock_client(True)
        client.get.return_value = self.USER_JSON
        endpoint = UserEndpoint(client)

        result = endpoint.get_user(user_id="u1")

        self.assertIsInstance(result, UserModel)

    def test_get_user_positional_convert_results_still_works_at_runtime(self):
        # Regression coverage for the PR #31 review finding: the @overload
        # set makes the Literal[True]/Literal[False] overloads keyword-only
        # in one variant and positional-required in another specifically so
        # a fully positional call like this still resolves to the precise
        # type under mypy, not just at runtime. This test only proves the
        # runtime half (overloads don't affect execution); the static half
        # is proven by the mypy scratch check in the PR description.
        client = self._mock_client(True)
        client.get.return_value = self.USER_JSON
        endpoint = UserEndpoint(client)

        result = endpoint.get_user(None, "u1", True)

        self.assertIsInstance(result, UserModel)

    def test_draft_endpoint_honors_false_client_default(self):
        client = self._mock_client(False)
        client.get.return_value = {"draft_id": "d1", "status": "complete"}
        endpoint = DraftEndpoint(client)

        result = endpoint.get_draft_by_id("d1")

        self.assertEqual(result, {"draft_id": "d1", "status": "complete"})

    def test_player_endpoint_honors_false_client_default(self):
        client = self._mock_client(False)
        players_payload = {"p1": {"player_id": "p1", "first_name": "A", "last_name": "B"}}
        client.get.return_value = players_payload
        endpoint = PlayerEndpoint(client)

        # Bypass the on-disk player cache entirely (unrelated to this
        # test), matching the pattern used in test_endpoint_player.py.
        with patch.object(endpoint, '_is_cache_valid', return_value=False), \
                patch.object(endpoint, '_save_cache'):
            result = endpoint.get_all_players()

        self.assertEqual(result, players_payload)

    def test_nfl_endpoint_honors_false_client_default(self):
        client = self._mock_client(False)
        client.get.return_value = [{"week": 1, "home": "SF", "away": "KC"}]
        endpoint = NFLEndpoint(client)

        result = endpoint.get_schedule(2024)

        self.assertEqual(result, [{"week": 1, "home": "SF", "away": "KC"}])


class TestConvertResultsReadIsStrictForDuckTypedClients(unittest.TestCase):
    """
    An endpoint can be constructed against any object exposing `.get()` --
    not necessarily a real SleeperClient (e.g. a caller's own test double or
    wrapper). Reading `self.client.convert_results` is deliberately strict
    (no `getattr(..., CONVERT_RESULTS)` fallback to the module default): a
    client-like object is expected to carry this attribute the same way a
    real `SleeperClient` does. A client missing it fails loudly with
    `AttributeError` when a call omits `convert_results` and needs to
    resolve the default, rather than silently inheriting
    `sleeper_api.config.CONVERT_RESULTS` as if nothing were wrong (PR #31
    review discussion -- a wrapper/proxy that forgets to forward this
    attribute should surface immediately, not return silently-different
    types down the line).

    A per-call `convert_results=` argument still bypasses this entirely --
    the client is never consulted when the caller says explicitly what they
    want.
    """

    class BareClient:
        """Implements only .get() -- no convert_results attribute at all."""
        def __init__(self, payload):
            self.payload = payload

        def get(self, endpoint, params=None):
            return self.payload

    ROSTER_JSON = [{
        "roster_id": 1, "owner_id": "u1", "league_id": "l1",
        "players": [], "starters": [], "settings": {}, "reserve": [],
    }]

    def test_missing_convert_results_attribute_raises_on_omitted_call(self):
        client = self.BareClient(self.ROSTER_JSON)
        endpoint = LeagueEndpoint(client)

        with self.assertRaises(AttributeError):
            endpoint.get_rosters("league1")

    def test_missing_convert_results_attribute_is_fine_with_explicit_override(self):
        # An explicit per-call convert_results= never needs to read
        # self.client.convert_results at all, so a client missing the
        # attribute works fine as long as every call is explicit about it.
        client = self.BareClient(self.ROSTER_JSON)
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1", convert_results=True)

        self.assertIsInstance(result[0], RosterModel)


if __name__ == '__main__':
    unittest.main()
