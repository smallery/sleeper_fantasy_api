"""Tests for the ProjectionsEndpoint class."""
import json
import threading
from unittest.mock import Mock

import pytest

from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
from sleeper_api.exceptions import SleeperAPIError
from sleeper_api.persistent_cache import PersistentCache


def _raw(data: dict) -> bytes:
    """Encode a dict the way the (mocked) Sleeper API would send it, for
    stubbing `mock_client.get_raw.return_value`/`side_effect`. Since #15,
    `ProjectionsEndpoint` fetches via `client.get_raw()` (bytes) rather than
    `client.get()` (parsed dict), so tests that used to hand a dict straight
    to `mock_client.get` now hand its encoded bytes to `mock_client.get_raw`.
    """
    return json.dumps(data).encode("utf-8")


class TestProjectionsEndpoint:
    """Test cases for ProjectionsEndpoint."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock SleeperClient."""
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        """Create a mock PersistentCache."""
        return Mock(spec=PersistentCache)

    @pytest.fixture
    def projections_endpoint(self, mock_client, mock_cache):
        """Create a ProjectionsEndpoint instance with mocked dependencies."""
        return ProjectionsEndpoint(mock_client, mock_cache)

    def test_get_projections_from_cache(self, projections_endpoint, mock_cache):
        """Test getting projections from cache."""
        # Arrange
        cached_data = {"player1": {"pts_ppr": 15.5}}
        mock_cache.get.return_value = cached_data

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == cached_data
        mock_cache.get.assert_called_once_with("projections:2024:1")

    def test_get_projections_from_api(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projections from API when not cached."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0}}
        raw = _raw(api_data)
        mock_client.get_raw.return_value = raw

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == api_data
        mock_client.get_raw.assert_called_once_with("projections/nfl/regular/2024/1")
        mock_client.get.assert_not_called()

    def test_get_projections_from_api_caches_raw_bytes_verbatim(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """#15: the cache write must use set_bytes() with the exact response
        bytes, not set() with the parsed dict -- that re-encode is the cost
        #15 removes.
        """
        # Arrange
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0}}
        raw = _raw(api_data)
        mock_client.get_raw.return_value = raw

        # Act
        projections_endpoint.get_projections(2024, 1)

        # Assert
        mock_cache.set_bytes.assert_called_once_with("projections:2024:1", raw, ttl_hours=24.0)
        mock_cache.set.assert_not_called()

    def test_get_projections_graceful_degradation(self, projections_endpoint, mock_client, mock_cache):
        """Test that failed projection fetch returns empty dict."""
        # Arrange
        mock_cache.get.return_value = None
        mock_client.get_raw.side_effect = SleeperAPIError("API error", status_code=500)

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == {}

    def test_get_projections_404_returns_empty_dict(self, projections_endpoint, mock_client, mock_cache):
        """get_raw() returns None for a 404 (matching get()'s contract);
        get_projections() must degrade to {} rather than crash on json.loads(None).
        """
        # Arrange
        mock_cache.get.return_value = None
        mock_client.get_raw.return_value = None

        # Act
        result = projections_endpoint.get_projections(2024, 1)

        # Assert
        assert result == {}
        mock_cache.set_bytes.assert_not_called()

    def test_get_scoring_type_ppr(self, projections_endpoint, mock_client):
        """Test scoring type detection for PPR league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 1.0}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_ppr"

    def test_get_scoring_type_half_ppr(self, projections_endpoint, mock_client):
        """Test scoring type detection for half-PPR league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 0.5}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_half_ppr"

    def test_get_scoring_type_standard(self, projections_endpoint, mock_client):
        """Test scoring type detection for standard league."""
        # Arrange
        mock_client.get.return_value = {
            "scoring_settings": {"rec": 0.0}
        }

        # Act
        result = projections_endpoint.get_scoring_type("league123")

        # Assert
        assert result == "pts_std"

    def test_calculate_team_projection(self, projections_endpoint):
        """Test calculating team projection from starters."""
        # Arrange
        starters = ["player1", "player2", "player3"]
        projections = {
            "player1": {"pts_ppr": 15.5},
            "player2": {"pts_ppr": 12.3},
            "player3": {"pts_ppr": 8.7},
        }

        # Act
        result = projections_endpoint.calculate_team_projection(
            starters, projections, "pts_ppr"
        )

        # Assert
        assert result == 36.5

    def test_calculate_team_projection_with_missing_players(self, projections_endpoint):
        """Test team projection when some players have no projections."""
        # Arrange
        starters = ["player1", "player2", "player3"]
        projections = {
            "player1": {"pts_ppr": 15.5},
            # player2 missing
            "player3": {"pts_ppr": 8.7},
        }

        # Act
        result = projections_endpoint.calculate_team_projection(
            starters, projections, "pts_ppr"
        )

        # Assert
        assert result == 24.2  # Only counts player1 and player3

    def test_get_player_projection_found(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projection for a single player."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {
            "player1": {"pts_ppr": 15.5, "rec": 5, "rec_yd": 60},
            "player2": {"pts_ppr": 12.0, "rush_yd": 80}
        }
        mock_client.get_raw.return_value = _raw(api_data)

        # Act
        result = projections_endpoint.get_player_projection("player1", 2024, 1)

        # Assert
        assert result == {"pts_ppr": 15.5, "rec": 5, "rec_yd": 60}

    def test_get_player_projection_not_found(self, projections_endpoint, mock_client, mock_cache):
        """Test getting projection for player not in dataset."""
        # Arrange
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5}}
        mock_client.get_raw.return_value = _raw(api_data)

        # Act
        result = projections_endpoint.get_player_projection("player999", 2024, 1)

        # Assert
        assert result is None

    def test_get_player_projection_uses_cache(self, projections_endpoint, mock_cache):
        """Test that get_player_projection uses cached data."""
        # Arrange
        cached_data = {
            "player1": {"pts_ppr": 15.5, "pass_yd": 300},
            "player2": {"pts_ppr": 10.0}
        }
        mock_cache.get.return_value = cached_data

        # Act
        result = projections_endpoint.get_player_projection("player1", 2024, 1)

        # Assert
        assert result == {"pts_ppr": 15.5, "pass_yd": 300}
        mock_cache.get.assert_called_once_with("projections:2024:1")

    def test_get_season_projections_specific_weeks(self, projections_endpoint, mock_client, mock_cache):
        """Test fetching projections for specific weeks."""
        # Arrange
        mock_cache.get.return_value = None
        week1_data = {"player1": {"pts_ppr": 15.5}}
        week2_data = {"player1": {"pts_ppr": 12.0}}
        mock_client.get_raw.side_effect = [_raw(week1_data), _raw(week2_data)]

        # Act
        result = projections_endpoint.get_season_projections(2024, weeks=[1, 2])

        # Assert
        assert len(result) == 2
        assert result[1] == week1_data
        assert result[2] == week2_data
        assert mock_client.get_raw.call_count == 2

    def test_get_season_projections_all_weeks(self, projections_endpoint, mock_client, mock_cache):
        """Test fetching projections for all 18 weeks."""
        # Arrange
        mock_cache.get.return_value = None
        mock_client.get_raw.return_value = _raw({"player1": {"pts_ppr": 15.5}})

        # Act
        result = projections_endpoint.get_season_projections(2024)

        # Assert
        assert len(result) == 18
        assert all(week in result for week in range(1, 19))
        assert mock_client.get_raw.call_count == 18

    def test_get_season_projections_handles_failures(self, projections_endpoint, mock_client, mock_cache):
        """Test that failed weeks don't stop other weeks from fetching."""
        # Arrange
        mock_cache.get.return_value = None
        week1_data = {"player1": {"pts_ppr": 15.5}}

        def side_effect(endpoint):
            if "week/1" in endpoint or endpoint.endswith("/1"):
                return _raw(week1_data)
            raise Exception("API Error")

        mock_client.get_raw.side_effect = side_effect

        # Act
        result = projections_endpoint.get_season_projections(2024, weeks=[1, 2])

        # Assert
        assert result[1] == week1_data
        assert result[2] == {}

    def test_get_season_projections_concurrent_matches_sequential(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """Concurrency must not change the result, only the timing."""
        # Arrange
        mock_cache.get.return_value = None
        weeks = list(range(1, 11))

        def side_effect(endpoint):
            week = int(endpoint.rsplit("/", 1)[1])
            return _raw({"player1": {"pts_ppr": float(week)}})

        mock_client.get_raw.side_effect = side_effect

        # Act
        sequential = projections_endpoint.get_season_projections(2024, weeks=weeks)
        concurrent = projections_endpoint.get_season_projections(
            2024, weeks=weeks, max_workers=8
        )

        # Assert
        assert concurrent == sequential
        assert list(concurrent.keys()) == weeks
        assert concurrent[7] == {"player1": {"pts_ppr": 7.0}}

    def test_get_season_projections_concurrent_fans_out(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """Verify the work actually overlaps rather than running in series."""
        # Arrange
        mock_cache.get.return_value = None
        barrier = threading.Barrier(4, timeout=5)

        def side_effect(endpoint):
            # Blocks until 4 threads arrive; raises BrokenBarrierError on
            # timeout if the fetches are running sequentially.
            barrier.wait()
            return _raw({"player1": {"pts_ppr": 1.0}})

        mock_client.get_raw.side_effect = side_effect

        # Act
        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2, 3, 4], max_workers=4
        )

        # Assert
        assert not barrier.broken
        assert len(result) == 4

    @pytest.mark.parametrize("max_workers", [0, -5, 1])
    def test_get_season_projections_low_worker_counts_run_sequentially(
        self, projections_endpoint, mock_client, mock_cache, max_workers
    ):
        """Values below 1 are clamped rather than raising."""
        # Arrange
        mock_cache.get.return_value = None
        mock_client.get_raw.side_effect = [
            _raw({"player1": {"pts_ppr": 15.5}}),
            _raw({"player1": {"pts_ppr": 12.0}}),
        ]

        # Act
        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2], max_workers=max_workers
        )

        # Assert -- ordered side_effect list only holds if fetches are serial
        assert result == {1: {"player1": {"pts_ppr": 15.5}}, 2: {"player1": {"pts_ppr": 12.0}}}

    def test_get_season_projections_concurrent_handles_failures(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """A week that raises degrades to {} without taking the others down."""
        # Arrange
        mock_cache.get.return_value = None

        def side_effect(endpoint):
            if endpoint.endswith("/2"):
                raise Exception("API Error")
            return _raw({"player1": {"pts_ppr": 15.5}})

        mock_client.get_raw.side_effect = side_effect

        # Act
        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2, 3], max_workers=4
        )

        # Assert
        assert result[1] == {"player1": {"pts_ppr": 15.5}}
        assert result[2] == {}
        assert result[3] == {"player1": {"pts_ppr": 15.5}}

    def test_get_player_season_projections(self, projections_endpoint, mock_client, mock_cache):
        """Test fetching single player across multiple weeks."""
        # Arrange
        mock_cache.get.return_value = None
        week1_data = {"player1": {"pts_ppr": 15.5, "rec": 5}, "player2": {"pts_ppr": 10.0}}
        week2_data = {"player1": {"pts_ppr": 12.0, "rec": 4}, "player2": {"pts_ppr": 8.0}}
        mock_client.get_raw.side_effect = [_raw(week1_data), _raw(week2_data)]

        # Act
        result = projections_endpoint.get_player_season_projections("player1", 2024, weeks=[1, 2])

        # Assert
        assert len(result) == 2
        assert result[1] == {"pts_ppr": 15.5, "rec": 5}
        assert result[2] == {"pts_ppr": 12.0, "rec": 4}

    def test_get_player_season_projections_missing_player(self, projections_endpoint, mock_client, mock_cache):
        """Test fetching player that doesn't exist in some weeks."""
        # Arrange
        mock_cache.get.return_value = None
        week1_data = {"player1": {"pts_ppr": 15.5}}
        week2_data = {"player2": {"pts_ppr": 10.0}}  # player1 not in week 2
        mock_client.get_raw.side_effect = [_raw(week1_data), _raw(week2_data)]

        # Act
        result = projections_endpoint.get_player_season_projections("player1", 2024, weeks=[1, 2])

        # Assert
        assert result[1] == {"pts_ppr": 15.5}
        assert result[2] is None

    # -- fields filter -- issue #16 ------------------------------------------

    def test_get_projections_fields_filters_cache_hit(
        self, projections_endpoint, mock_cache
    ):
        """A cache hit must also be filtered -- fields isn't only a
        fetch-time concern, since most calls after the first are cache hits.
        """
        cached_data = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5, "rush_yd": 0},
            "player2": {"pts_ppr": 9.0, "pts_half_ppr": 8.0, "rec_yd": 40},
        }
        mock_cache.get.return_value = cached_data

        result = projections_endpoint.get_projections(2024, 1, fields=("pts_ppr",))

        assert result == {
            "player1": {"pts_ppr": 15.5},
            "player2": {"pts_ppr": 9.0},
        }

    def test_get_projections_fields_filters_cache_miss(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """A cache miss (fresh API fetch) must also be filtered."""
        mock_cache.get.return_value = None
        api_data = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }
        mock_client.get_raw.return_value = _raw(api_data)

        result = projections_endpoint.get_projections(2024, 1, fields=("pts_ppr",))

        assert result == {"player1": {"pts_ppr": 15.5}}

    def test_get_projections_fields_does_not_shrink_what_is_cached(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """#16's chosen strategy: the cache always stores the FULL payload,
        regardless of `fields` -- filtering only affects what's returned to
        this call. See get_projections()'s "Caching and `fields`" docstring
        note and the #15/#16 PR description for the reasoning. This is also
        what satisfies #16's acceptance criterion "cache cannot return a
        filtered payload to a caller that asked for the full one": the cache
        never holds anything but the full payload in the first place.
        """
        mock_cache.get.return_value = None
        api_data = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }
        raw = _raw(api_data)
        mock_client.get_raw.return_value = raw

        projections_endpoint.get_projections(2024, 1, fields=("pts_ppr",))

        # The bytes handed to the cache are the untouched, full API response
        # -- not something re-serialized from the filtered dict.
        mock_cache.set_bytes.assert_called_once_with("projections:2024:1", raw, ttl_hours=24.0)

    def test_get_projections_no_fields_arg_is_unfiltered_and_unchanged(
        self, projections_endpoint, mock_client, mock_cache
    ):
        """Explicit acceptance check from #16: existing calls (no `fields`
        argument at all) must be unaffected.
        """
        mock_cache.get.return_value = None
        api_data = {"player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5}}
        mock_client.get_raw.return_value = _raw(api_data)

        result = projections_endpoint.get_projections(2024, 1)

        assert result == api_data

    def test_get_projections_fields_missing_field_is_simply_absent(
        self, projections_endpoint, mock_cache
    ):
        """Requesting a field a player's data doesn't have must not fill in
        a default -- it's just absent from that player's dict.
        """
        mock_cache.get.return_value = {"player1": {"pts_ppr": 15.5}}

        result = projections_endpoint.get_projections(
            2024, 1, fields=("pts_ppr", "pts_std")
        )

        assert result == {"player1": {"pts_ppr": 15.5}}
        assert "pts_std" not in result["player1"]

    def test_get_player_projection_fields_filter(self, projections_endpoint, mock_cache):
        """fields must thread through get_player_projection()."""
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }

        result = projections_endpoint.get_player_projection(
            "player1", 2024, 1, fields=("pts_ppr",)
        )

        assert result == {"pts_ppr": 15.5}

    def test_get_season_projections_fields_filter(self, projections_endpoint, mock_cache):
        """fields must thread through get_season_projections() for every week."""
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }

        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2], fields=("pts_ppr",)
        )

        assert result == {
            1: {"player1": {"pts_ppr": 15.5}},
            2: {"player1": {"pts_ppr": 15.5}},
        }

    def test_get_player_season_projections_fields_filter(self, projections_endpoint, mock_cache):
        """fields must thread through get_player_season_projections()."""
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }

        result = projections_endpoint.get_player_season_projections(
            "player1", 2024, weeks=[1], fields=("pts_ppr",)
        )

        assert result == {1: {"pts_ppr": 15.5}}

    # -- fields as a one-shot iterable -- PR #32 review ----------------------
    #
    # `fields` is typed Optional[Iterable[str]], so a generator is a legal
    # argument. get_season_projections() forwards the *same* fields object to
    # a separate get_projections() call per week; without materializing it
    # once up front, the first week's filter would consume the generator and
    # every later week would silently filter against an empty set -- no
    # exception, no warning, just empty per-player dicts easily misread as
    # "no data this week."

    def test_get_season_projections_fields_generator_sequential(
        self, projections_endpoint, mock_cache
    ):
        """A one-shot generator passed as `fields` must filter every week
        identically under sequential (max_workers=1, the default) fetching,
        not just the first week that happens to touch it.
        """
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }
        fields_gen = (f for f in ("pts_ppr",))

        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2, 3], fields=fields_gen, max_workers=1
        )

        expected_week = {"player1": {"pts_ppr": 15.5}}
        assert result == {1: expected_week, 2: expected_week, 3: expected_week}

    def test_get_season_projections_fields_generator_concurrent(
        self, projections_endpoint, mock_cache
    ):
        """Same guarantee under max_workers > 1, where -- absent a fix --
        this would additionally be a race: whichever worker thread reaches
        the shared generator first would "win" its contents, and the bug
        would reproduce nondeterministically across runs.

        Deterministic here (no sleeps, no timing dependency): the fields
        argument is materialized into a frozenset once, before the thread
        pool is even created, so every worker thread only ever sees an
        already-materialized, repeatedly-iterable frozenset -- never the
        original generator. There is no window in which two threads could
        race over it.
        """
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }
        fields_gen = (f for f in ("pts_ppr",))

        result = projections_endpoint.get_season_projections(
            2024, weeks=[1, 2, 3, 4], fields=fields_gen, max_workers=4
        )

        expected_week = {"player1": {"pts_ppr": 15.5}}
        assert result == {
            1: expected_week,
            2: expected_week,
            3: expected_week,
            4: expected_week,
        }

    def test_get_player_season_projections_fields_generator(
        self, projections_endpoint, mock_cache
    ):
        """get_player_season_projections() inherits the same guarantee
        through get_season_projections() -- explicitly called out in the
        PR #32 review as sharing the bug through this path.
        """
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5},
        }
        fields_gen = (f for f in ("pts_ppr",))

        result = projections_endpoint.get_player_season_projections(
            "player1", 2024, weeks=[1, 2, 3], fields=fields_gen
        )

        assert result == {
            1: {"pts_ppr": 15.5},
            2: {"pts_ppr": 15.5},
            3: {"pts_ppr": 15.5},
        }

    def test_materialize_fields_returns_none_for_none(self):
        """None must pass through unchanged, not become an empty frozenset
        (which would silently filter every field out instead of returning
        everything, per _filter_projection_fields()'s None-means-unfiltered
        contract).
        """
        from sleeper_api.endpoints.projections_endpoint import _materialize_fields

        assert _materialize_fields(None) is None

    def test_materialize_fields_consumes_generator_into_reusable_frozenset(self):
        """Direct unit check of the helper itself: given a one-shot
        generator, it returns a frozenset containing the generator's full
        contents, usable any number of times afterward.
        """
        from sleeper_api.endpoints.projections_endpoint import _materialize_fields

        gen = (f for f in ("pts_ppr", "pts_half_ppr"))
        materialized = _materialize_fields(gen)

        assert materialized == frozenset({"pts_ppr", "pts_half_ppr"})
        # Iterating it twice must yield the same thing both times -- the
        # entire point of materializing it.
        assert set(materialized) == set(materialized) == {"pts_ppr", "pts_half_ppr"}

    def test_filtered_projections_compose_with_calculate_team_projection(
        self, projections_endpoint, mock_cache
    ):
        """Explicit acceptance check from #16: a fields-filtered payload must
        still work with calculate_team_projection(), as long as the
        requested fields include the scoring_type being used.
        """
        mock_cache.get.return_value = {
            "player1": {"pts_ppr": 15.5, "pts_half_ppr": 14.0, "rec": 5, "rush_yd": 0},
            "player2": {"pts_ppr": 9.0, "pts_half_ppr": 8.0, "rec_yd": 40},
        }
        filtered = projections_endpoint.get_projections(2024, 1, fields=("pts_ppr",))

        total = projections_endpoint.calculate_team_projection(
            ["player1", "player2"], filtered, scoring_type="pts_ppr"
        )

        assert total == 24.5
