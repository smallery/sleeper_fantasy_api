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


class TestConvertResultsFallsBackForDuckTypedClients(unittest.TestCase):
    """
    An endpoint can be constructed against any object exposing `.get()` --
    not necessarily a real SleeperClient (e.g. a caller's own test double).
    Such an object has no `.convert_results` attribute, so the lookup falls
    back to the same CONVERT_RESULTS default a bare `SleeperClient()` gets,
    instead of raising AttributeError.
    """

    class BareClient:
        """Implements only .get() -- no convert_results attribute at all."""
        def __init__(self, payload):
            self.payload = payload

        def get(self, endpoint, params=None):
            return self.payload

    def test_missing_convert_results_attribute_falls_back_to_default(self):
        roster_json = [{
            "roster_id": 1, "owner_id": "u1", "league_id": "l1",
            "players": [], "starters": [], "settings": {}, "reserve": [],
        }]
        client = self.BareClient(roster_json)
        endpoint = LeagueEndpoint(client)

        result = endpoint.get_rosters("league1")

        # CONVERT_RESULTS defaults True, so the fallback should convert.
        self.assertIsInstance(result[0], RosterModel)


if __name__ == '__main__':
    unittest.main()
