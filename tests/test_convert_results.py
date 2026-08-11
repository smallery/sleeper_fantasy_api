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
from sleeper_api.exceptions import SleeperAPIError


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


class TestCollectionEndpointsOn404(unittest.TestCase):
    """A 404 collection must be [] on both paths, not None and not a crash.

    SleeperClient.get() returns None for a 404. Twelve collection methods passed
    that straight through: the raw path returned None against a declared
    List[...] (a lie the overloads now publish to type checkers), and the
    convert path raised "'NoneType' object is not iterable" building models.
    """

    CASES = [
        (LeagueEndpoint, "get_rosters", ("1",)),
        (LeagueEndpoint, "get_users", ("1",)),
        (LeagueEndpoint, "get_matchups", ("1", 1)),
        (LeagueEndpoint, "get_transactions", ("1", 1)),
        (LeagueEndpoint, "get_traded_picks", ("1",)),
        (LeagueEndpoint, "get_winners_bracket", ("1",)),
        (LeagueEndpoint, "get_losers_bracket", ("1",)),
        (DraftEndpoint, "get_draft_picks", ("1",)),
        (DraftEndpoint, "get_drafts_by_league", ("1",)),
        (DraftEndpoint, "get_traded_picks", ("1",)),
    ]

    def test_404_yields_an_empty_collection_on_both_paths(self):
        for cls, name, args in self.CASES:
            for convert in (True, False):
                with self.subTest(method=name, convert_results=convert):
                    client = MagicMock()
                    client.convert_results = convert
                    client.get.return_value = None
                    self.assertEqual(getattr(cls(client), name)(*args), [])


class TestScalarLookupOn404(unittest.TestCase):
    """A named-resource 404 must raise, not return None or crash.

    The collection guards cover methods that return lists; get_draft_by_id is a
    scalar lookup and was missed by that sweep. Before this, the raw path
    returned None against a declared Dict and the convert path crashed inside
    DraftModel.from_json(). Matches get_user()/get_league_by_id() (issue #17):
    a caller naming one resource gets an error when it does not exist.
    """

    def test_get_draft_by_id_raises_on_404(self):
        for convert in (True, False):
            with self.subTest(convert_results=convert):
                client = MagicMock()
                client.convert_results = convert
                client.get.return_value = None
                with self.assertRaises(SleeperAPIError) as ctx:
                    DraftEndpoint(client).get_draft_by_id("missing-id")
                self.assertEqual(ctx.exception.status_code, 404)
                self.assertIn("missing-id", str(ctx.exception))


class TestRemainingNoneSites(unittest.TestCase):
    """Every remaining client.get() site handles a 404 deliberately.

    Two earlier sweeps missed these: the collection sweep only matched methods
    returning lists, and NFLEndpoint's try/except shape defeated the regex.
    """

    def _client(self, convert):
        c = MagicMock()
        c.convert_results = convert
        c.get.return_value = None
        return c

    def test_named_resources_raise(self):
        from sleeper_api.endpoints.nfl_endpoint import NFLEndpoint
        for convert in (True, False):
            with self.subTest(convert_results=convert, method="get_team_depth_chart"):
                with self.assertRaises(SleeperAPIError):
                    NFLEndpoint(self._client(convert)).get_team_depth_chart("ZZZ")
            with self.subTest(convert_results=convert, method="get_nfl_state"):
                with self.assertRaises(SleeperAPIError):
                    LeagueEndpoint(self._client(convert)).get_nfl_state()

    def test_schedule_returns_an_empty_collection(self):
        from sleeper_api.endpoints.nfl_endpoint import NFLEndpoint
        raw = NFLEndpoint(self._client(False)).get_schedule(2026)
        self.assertEqual(raw, [])
        model = NFLEndpoint(self._client(True)).get_schedule(2026)
        self.assertEqual(model.games, [])

    def test_scoring_type_falls_back_instead_of_raising_attributeerror(self):
        from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
        from sleeper_api.persistent_cache import PersistentCache
        cache = MagicMock(spec=PersistentCache)
        cache.get.return_value = None
        self.assertEqual(
            ProjectionsEndpoint(self._client(True), cache).get_scoring_type("missing"),
            "pts_half_ppr",
        )

    def test_context_manager_is_annotated_for_downstream_checkers(self):
        # The README's primary pattern is `with SleeperClient() as client:`.
        # Without these annotations mypy binds `client` as Any and every result
        # reached through it goes unchecked.
        import inspect
        from sleeper_api.client import SleeperClient
        self.assertEqual(inspect.signature(SleeperClient.__enter__).return_annotation,
                         "SleeperClient")
        self.assertIsNot(inspect.signature(SleeperClient.__exit__).return_annotation,
                         inspect.Signature.empty)


class TestNoUnannotatedExports(unittest.TestCase):
    """No callable on the public surface may lack a return annotation.

    Two earlier versions of this test gave false confidence:

    * `inspect.getmembers(cls, inspect.isfunction)` silently skips
      classmethods -- accessing a `@classmethod` through its class yields a
      bound method, for which `isfunction` is False. The four exported
      factories were therefore never checked, which is precisely the category
      the invariant exists to protect. This walks `vars(cls)` and unwraps the
      descriptors instead.
    * Starting only from `sleeper_api.__all__` missed types reachable through
      exported signatures. `LeagueEndpoint.get_nfl_state()` returns
      `NFLStateModel`, so it is public whether or not it is exported. This
      follows return annotations to find them.
    """

    SKIP = {"__init__", "__init_subclass__", "__subclasshook__", "__new__"}

    @staticmethod
    def _callables(cls):
        """Yield (name, function) for every callable defined on `cls`.

        Uses raw `vars()` descriptors so classmethods and staticmethods are
        included -- `inspect.isfunction` drops them.
        """
        import inspect
        for name, raw in vars(cls).items():
            func = raw.__func__ if isinstance(raw, (classmethod, staticmethod)) else raw
            if inspect.isfunction(func):
                yield name, func

    def _public_classes(self):
        """Exported classes, plus every class reachable via a return annotation."""
        import inspect
        import sleeper_api

        seen, queue = {}, [getattr(sleeper_api, n) for n in sleeper_api.__all__]
        while queue:
            obj = queue.pop()
            if not inspect.isclass(obj) or obj in seen.values():
                continue
            if not obj.__module__.startswith("sleeper_api"):
                continue
            seen[obj.__qualname__] = obj
            for _, func in self._callables(obj):
                try:
                    ret = inspect.signature(func).return_annotation
                except (ValueError, TypeError):
                    continue
                for candidate in (ret, *getattr(ret, "__args__", ())):
                    if inspect.isclass(candidate):
                        queue.append(candidate)
        return seen

    def test_every_public_callable_is_annotated(self):
        import inspect

        gaps = []
        for cls_name, cls in self._public_classes().items():
            for name, func in self._callables(cls):
                if name in self.SKIP:
                    continue
                if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
                    continue
                try:
                    sig = inspect.signature(func)
                except (ValueError, TypeError):
                    continue
                if sig.return_annotation is inspect.Signature.empty:
                    gaps.append(f"{cls_name}.{name}")
        self.assertEqual(sorted(gaps), [], f"unannotated public callables: {sorted(gaps)}")

    def test_the_invariant_actually_sees_classmethods(self):
        # Guards the bug this test previously had: if the walk misses
        # classmethods, the factory annotations could regress unnoticed.
        from sleeper_api.models.draft import DraftModel
        names = {n for n, _ in self._callables(DraftModel)}
        self.assertIn("from_json", names)

    def test_public_module_functions_are_annotated(self):
        """Module-level public functions are part of the surface too.

        The class walk above cannot see them -- it queues classes from
        `__all__` and inspects their methods -- so `config.get_current_season()`
        shipped unannotated and resolved to `Any` downstream while the
        class-based invariant passed. Third blind spot in the same test, hence
        this second assertion rather than a third hand-written sweep.
        """
        import importlib
        import inspect
        import pkgutil

        import sleeper_api

        gaps = []
        for mod_info in pkgutil.walk_packages(sleeper_api.__path__, "sleeper_api."):
            module = importlib.import_module(mod_info.name)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_"):
                    continue
                if func.__module__ != module.__name__:
                    continue          # re-exported, checked where it is defined
                sig = inspect.signature(func)
                if sig.return_annotation is inspect.Signature.empty:
                    gaps.append(f"{mod_info.name}.{name} (return)")
                for pname, param in sig.parameters.items():
                    if pname == "self":
                        continue
                    if param.annotation is inspect.Parameter.empty:
                        gaps.append(f"{mod_info.name}.{name}({pname})")
        self.assertEqual(sorted(gaps), [], f"unannotated public module functions: {sorted(gaps)}")

