"""
This module provides the `ProjectionsEndpoint` class for interacting
with player projections from the Sleeper API.

Note: This uses an undocumented Sleeper endpoint that may change.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, FrozenSet, Iterable, List, Optional

from ..exceptions import SleeperAPIError
from ..persistent_cache import PersistentCache

logger = logging.getLogger(__name__)

# NFL regular season has 18 weeks
NFL_REGULAR_SEASON_WEEKS = 18

# Ceiling on concurrent week fetches. Each week's payload is multiple megabytes,
# so this bounds peak memory as much as it bounds connections, and it stays
# under the client session's pool_maxsize of 20.
MAX_CONCURRENT_WEEK_FETCHES = 8


def _materialize_fields(fields: Optional[Iterable[str]]) -> Optional[FrozenSet[str]]:
    """
    Materialize a caller-supplied `fields` iterable into a `frozenset`, once,
    at the boundary where it enters this module.

    `fields` is typed `Optional[Iterable[str]]` so any iterable is accepted
    -- including a one-shot generator or iterator. That is fine for a single
    use, but `get_season_projections()` (and, through it,
    `get_player_season_projections()`) forwards the *same* `fields` object
    to a separate `get_projections()` call per week. If that object is a
    generator, the first week's filter exhausts it and every later week
    silently filters against an empty set -- empty per-player dicts, no
    exception, no warning, easily misread as "Sleeper had no data for this
    week." Under `max_workers > 1` it's worse: whichever week's thread
    happens to consume the generator first wins, so the bug is
    nondeterministic across runs. See PR #32 review.

    Calling this once, immediately, at every public method that accepts
    `fields` -- before it is used or forwarded anywhere else -- closes this
    off structurally: a `frozenset` can be iterated any number of times and
    shared read-only across threads safely, so no downstream call site (this
    module has several) needs to know or care whether the original argument
    was list-like or a one-shot iterator.

    Args:
        fields: Caller-supplied iterable of field names, or None.

    Returns:
        None if `fields` is None, else a frozenset of its contents.
    """
    if fields is None:
        return None
    return frozenset(fields)


def _filter_projection_fields(
    projections: Dict[str, Dict], fields: Optional[Iterable[str]]
) -> Dict[str, Dict]:
    """
    Trim each player's projection dict down to just `fields`, if given.

    This is the read side of the #15/#16 strategy decision: the cache always
    stores (and get_projections() always fetches) the complete payload --
    only the value handed back to *this* caller is filtered. See
    get_projections()'s docstring for the full reasoning.

    Args:
        projections: Full player_id -> projection-stats mapping.
        fields: Iterable of field names to keep in each player's dict, or
            None to return every field.

    Returns:
        `projections` itself, unchanged, if `fields` is None -- so an
        unfiltered call costs nothing extra and existing callers see no
        behavior change. Otherwise a new dict of new per-player dicts,
        each containing only keys present in `fields` (missing fields are
        simply absent, not filled in with a default).
    """
    if fields is None:
        return projections

    field_set = frozenset(fields)
    return {
        player_id: {k: v for k, v in player_data.items() if k in field_set}
        for player_id, player_data in projections.items()
    }


class ProjectionsEndpoint:
    """
    Projections endpoint class to fetch player projections.

    Uses an undocumented Sleeper endpoint to get projected points.
    Results are cached in persistent file storage to minimize API calls.
    """

    def __init__(self, client, persistent_cache: Optional[PersistentCache] = None):
        """
        Initialize the projections endpoint.

        Args:
            client: SleeperClient instance.
            persistent_cache: Optional PersistentCache instance for caching projections.
        """
        self.client = client
        self.persistent_cache = persistent_cache or PersistentCache(default_ttl_hours=24.0)

    def get_projections(
        self, season: int, week: int, fields: Optional[Iterable[str]] = None
    ) -> Dict[str, Dict]:
        """
        Fetch all player projections for a specific week.

        Uses an undocumented Sleeper endpoint to get projected stats.
        Results are cached in persistent file storage to minimize API calls.

        Args:
            season: NFL season year (e.g., 2024).
            week: Week number (1-18).
            fields: Optional iterable of projection field names to keep in
                the returned data, e.g. ``("pts_ppr",)``. When given, each
                player's dict in the result is trimmed to just these fields.
                Defaults to None, which returns every field -- existing
                calls are unaffected. See "Caching and `fields`" below for
                what this does and doesn't change about the cache. (#16)

        Returns:
            Dict mapping player_id -> projection stats including:
            - pts_std: Standard scoring projected points
            - pts_half_ppr: Half-PPR projected points
            - pts_ppr: Full PPR projected points
            - Individual stat projections (passing_yards, rushing_yards, etc.)
            If `fields` is given, each player's dict contains only the keys
            present in `fields` (a field the API didn't return for that
            player is simply absent, not filled in with a default).

        Note:
            This endpoint returns PROJECTIONS (pre-game predictions), not actuals.

            For actual fantasy points after games are played:
            - Use LeagueEndpoint.get_matchups(league_id, week)
            - Returns MatchupModel with actual points in matchup.points field
            - Only includes players rostered in that specific league

            For league-agnostic actual NFL stats (all players), use external APIs:
            - ESPN API, NFL.com API, SportRadar, etc.

            This returns ALL projection data from the Sleeper API.
            Use get_player_projection() to fetch a single player.
            Returns empty dict on failure for graceful degradation.

        Caching and `fields` (#15 / #16):
            The cache always stores -- and this method always fetches -- the
            complete, unfiltered payload for a (season, week); `fields` only
            trims what's handed back to *this* call. Two designs were
            considered for #16 (filter at cache-write time, keyed by field
            set, vs. always cache the full payload and filter on read) and
            the second was chosen, for two reasons that both trace back to
            #15 landing first:

            1. #15 already made caching the *raw response bytes* (not the
               parsed dict) the cheap path for a cache write -- see
               PersistentCache.set_bytes(). A field-filtered payload can't
               reuse that: filtering requires a parsed dict, so a
               filter-then-cache design would have reintroduced the
               parse/filter/re-serialize cost #15 exists to remove, and paid
               it on every distinct field-set a caller ever asks for.
            2. Filtering at write time also means the cache key must fold in
               the field set (or a narrow fetch poisons the cache for a
               later full request, and vice versa) -- one more axis of cache
               keying to get right, for a win that's about caller memory,
               not disk or network.

            Filtering on read costs nothing when `fields` is None (the
            filter is a no-op passthrough -- see `_filter_projection_fields`),
            keeps exactly one cache entry per (season, week) no matter how
            many different `fields` values callers ask for, and makes "a
            filtered payload leaking to a caller that asked for the full
            one" structurally impossible, since the cache never holds
            anything but the full payload. The trade-off: this does not
            shrink the cache *directory* the way write-time filtering would
            (disk usage stays the ~581KB/week of the full payload,
            regardless of `fields`) -- only a caller's own copy of the
            result gets smaller. That's the win #16 asked for: the
            downstream memory pressure (10 weeks x ~9,400 players held per
            gunicorn worker) was about parsed-object memory, not disk.

        Example:
            >>> # Get projections (pre-game)
            >>> projections = endpoint.get_projections(2024, 1)
            >>> player_data = projections.get("player_id")
            >>> if player_data:
            >>>     print(f"Projected PPR: {player_data.get('pts_ppr')}")
            >>>
            >>> # Get actuals (post-game)
            >>> matchups = league_endpoint.get_matchups(league_id, 1)
            >>> for matchup in matchups:
            >>>     print(f"Actual points: {matchup.points}")
            >>>
            >>> # Only need PPR points? Trim what's returned (cache is
            >>> # unaffected -- still stores the full payload).
            >>> ppr_only = endpoint.get_projections(2024, 1, fields=("pts_ppr",))
        """
        # Materialize once, immediately -- see _materialize_fields(). A
        # generator passed here and used only within this one call would
        # already be safe, but doing it unconditionally at every public
        # entry point means the guarantee doesn't depend on which method a
        # caller happened to go through.
        fields = _materialize_fields(fields)

        cache_key = f"projections:{season}:{week}"

        # Check persistent file cache. Always the full payload -- see the
        # "Caching and `fields`" note above -- so filtering happens on every
        # path, cache hit or miss, in one place below.
        cached = self.persistent_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Loaded projections from cache for {season} week {week}")
            return _filter_projection_fields(cached, fields)

        # Fetch from API. Uses get_raw() rather than get() so the response
        # bytes the client already read can go straight to the cache via
        # set_bytes() -- no decode-then-re-encode round trip. See #15.
        try:
            endpoint = f"projections/nfl/regular/{season}/{week}"
            raw = self.client.get_raw(endpoint)

            if not raw:
                logger.warning(f"No projection data returned for {season} week {week}")
                return {}

            try:
                data = json.loads(raw)
            except ValueError as exc:
                raise SleeperAPIError("Invalid JSON response received") from exc

            if data:
                # Cache the raw bytes verbatim for 24 hours -- see #15.
                self.persistent_cache.set_bytes(cache_key, raw, ttl_hours=24.0)
                logger.info(f"Fetched projections for {season} week {week}")
                return _filter_projection_fields(data, fields)
            else:
                logger.warning(f"No projection data returned for {season} week {week}")
                return {}

        except SleeperAPIError as e:
            logger.warning(f"Failed to fetch projections: {e}")
            return {}  # Graceful degradation

    def get_player_projection(
        self,
        player_id: str,
        season: int,
        week: int,
        fields: Optional[Iterable[str]] = None,
    ) -> Optional[Dict]:
        """
        Fetch projection data for a single player.

        This is a convenience method that fetches all projections for the week
        (using cache) and returns just the specified player's data.

        Args:
            player_id: Sleeper player ID.
            season: NFL season year (e.g., 2024).
            week: Week number (1-18).
            fields: Optional iterable of projection field names to keep in
                the player's returned dict. See get_projections(). (#16)

        Returns:
            Dict with projection stats for the player, or None if not found.
            Includes all available fields such as:
            - pts_std, pts_half_ppr, pts_ppr (projected points)
            - pass_yd, pass_td, pass_int (passing stats)
            - rush_yd, rush_td (rushing stats)
            - rec, rec_yd, rec_td (receiving stats)
            - And other stat projections

        Example:
            >>> proj = endpoint.get_player_projection("4018", 2024, 1)
            >>> if proj:
            >>>     print(f"PPR Points: {proj.get('pts_ppr')}")
            >>>     print(f"Receptions: {proj.get('rec')}")
        """
        projections = self.get_projections(season, week, fields=fields)
        return projections.get(player_id)

    def _fetch_week(
        self, season: int, week: int, fields: Optional[Iterable[str]] = None
    ) -> Dict[str, Dict]:
        """
        Fetch one week's projections, degrading to an empty dict on any failure.

        Args:
            season: NFL season year.
            week: Week number.
            fields: Optional field filter, forwarded to get_projections(). (#16)

        Returns:
            Projections dict for the week, or {} if the fetch failed.
        """
        try:
            projections = self.get_projections(season, week, fields=fields)
            if projections:
                logger.debug(f"Fetched {len(projections)} players for week {week}")
            else:
                logger.warning(f"No projection data for week {week}")
            return projections
        except Exception as e:
            logger.error(f"Failed to fetch projections for week {week}: {e}")
            return {}

    def get_season_projections(
        self,
        season: int,
        weeks: Optional[List[int]] = None,
        max_workers: int = 1,
        fields: Optional[Iterable[str]] = None,
    ) -> Dict[int, Dict[str, Dict]]:
        """
        Fetch player projections for multiple weeks in a season.

        This is a convenience method for bulk-fetching projection data.
        Each week's data is fetched separately and cached independently.

        Args:
            season: NFL season year (e.g., 2024).
            weeks: List of week numbers to fetch. If None, fetches all 18 regular season weeks.
            max_workers: Number of weeks to fetch concurrently. Defaults to 1
                (sequential). Pass a higher value to fan out over a thread pool.
                Capped at 8; values below 1 are treated as 1. See the
                performance note below before reaching for it.
            fields: Optional iterable of projection field names to keep in
                each week's returned data. Forwarded to get_projections() for
                every week; the cache still always holds the full payload
                for each week regardless of this argument -- see
                get_projections()'s "Caching and `fields`" note. (#16)

        Returns:
            Dict mapping week number -> projections dict, in the order the weeks
            were requested. Identical whether or not concurrency is used.
            Example: {1: {"player1": {...}}, 2: {"player1": {...}}, ...}

        Note:
            - Weeks with no data available return empty dicts
            - Each week is cached independently (24-hour TTL)
            - Failed weeks are logged but don't stop other weeks from fetching

        Performance (measured against the live API, 2025 season, 18 weeks):
            A week of projections is roughly 0.55 MB and ~9,400 player entries,
            so 18 weeks is about 9.4 MB total -- less than you might assume.
            Sequentially that is ~0.8s on a warm connection, and an 8-way
            fan-out brings it to ~0.35s (~2.4x). The network portion alone
            parallelizes ~3.4x; the gap is the cache write, which is CPU-bound
            JSON serialization and holds the GIL.

            The win depends on connection reuse. Each worker needs its own
            pooled connection, and a TLS handshake to Sleeper costs ~0.3s --
            far more than the ~0.03s a warm request takes. Over a cold pool with
            only a few weeks, the fan-out can pay more in handshakes than it
            saves, and may be no faster or slightly slower. It pays off when the
            client is long-lived (connections already established) or when
            round-trip latency is high.

            Concurrent fetches also hold every requested week's payload in
            memory at once, trading memory for latency.

        Example:
            >>> # Fetch first 4 weeks
            >>> projections = endpoint.get_season_projections(2024, weeks=[1, 2, 3, 4])
            >>> week_1 = projections[1]
            >>>
            >>> # Fetch entire season
            >>> all_projections = endpoint.get_season_projections(2024)
            >>>
            >>> # Fetch the rest of the season concurrently
            >>> rest = endpoint.get_season_projections(
            ...     2024, weeks=list(range(10, 19)), max_workers=8
            ... )
        """
        # Materialize once, before `fields` is forwarded to more than one
        # week's fetch. This is THE critical spot for this guarantee: the
        # exact same `fields` object is about to be handed to a separate
        # get_projections() call per week (sequentially, or racing across
        # threads below), and get_projections()'s own materialization can't
        # help here -- by the time each call touches a shared generator, the
        # object itself is already partially or fully consumed by whichever
        # call reached it first. See _materialize_fields() and PR #32 review.
        fields = _materialize_fields(fields)

        if weeks is None:
            weeks = list(range(1, NFL_REGULAR_SEASON_WEEKS + 1))

        workers = min(max(max_workers, 1), MAX_CONCURRENT_WEEK_FETCHES, len(weeks) or 1)

        if workers == 1:
            return {week: self._fetch_week(season, week, fields=fields) for week in weeks}

        # ThreadPoolExecutor.map preserves input order, so the resulting dict is
        # keyed the same way the sequential path keys it.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = executor.map(
                lambda week: self._fetch_week(season, week, fields=fields), weeks
            )
            return dict(zip(weeks, results))

    def get_player_season_projections(
        self,
        player_id: str,
        season: int,
        weeks: Optional[List[int]] = None,
        max_workers: int = 1,
        fields: Optional[Iterable[str]] = None,
    ) -> Dict[int, Optional[Dict]]:
        """
        Fetch projections for a single player across multiple weeks.

        This is a convenience method for tracking one player's projections
        over time. Uses cached data from get_season_projections().

        Args:
            player_id: Sleeper player ID.
            season: NFL season year (e.g., 2024).
            weeks: List of week numbers to fetch. If None, fetches all 18 weeks.
            max_workers: Weeks to fetch concurrently. See get_season_projections().
            fields: Optional iterable of projection field names to keep in
                the player's returned dict for each week. See
                get_projections(). (#16)

        Returns:
            Dict mapping week number -> player projection data (or None if not found).
            Example: {1: {"pts_ppr": 15.5, ...}, 2: {"pts_ppr": 12.0, ...}}

        Example:
            >>> # Track QB across season
            >>> mahomes = endpoint.get_player_season_projections("4018", 2024)
            >>> for week, proj in mahomes.items():
            >>>     if proj:
            >>>         print(f"Week {week}: {proj.get('pts_ppr')} PPR points")
        """
        # Materialize here too, even though get_season_projections() would
        # materialize it anyway -- this call is itself a boundary a caller
        # can hand a one-shot iterable to, and this guarantee shouldn't
        # depend on tracing into what get_season_projections() happens to do
        # internally. Idempotent and cheap either way: re-wrapping an
        # already-materialized frozenset just makes another frozenset.
        fields = _materialize_fields(fields)
        season_data = self.get_season_projections(
            season, weeks, max_workers=max_workers, fields=fields
        )

        player_data = {}
        for week, projections in season_data.items():
            player_data[week] = projections.get(player_id)

        return player_data

    def get_scoring_type(self, league_id: str) -> str:
        """
        Determine which projection field to use based on league settings.

        Args:
            league_id: The league ID.

        Returns:
            Projection field name: 'pts_std', 'pts_half_ppr', or 'pts_ppr'.
        """
        try:
            endpoint = f"league/{league_id}"
            data = self.client.get(endpoint)

            # A missing league 404s to None. This method already degrades to a
            # sensible default on SleeperAPIError; None used to slip past that
            # as an AttributeError on the next line instead.
            if data is None:
                logger.warning(f"No league data for {league_id}; defaulting scoring type")
                return "pts_half_ppr"

            scoring_settings = data.get("scoring_settings", {})
            rec_points = scoring_settings.get("rec", 0.0)

            # Determine scoring type from reception points
            if rec_points >= 1.0:
                scoring_type = "pts_ppr"  # Full PPR
            elif rec_points >= 0.5:
                scoring_type = "pts_half_ppr"  # Half PPR
            else:
                scoring_type = "pts_std"  # Standard

            logger.debug(f"League {league_id} scoring type: {scoring_type}")
            return scoring_type

        except SleeperAPIError as e:
            logger.warning(f"Failed to get scoring type for league {league_id}: {e}")
            return "pts_half_ppr"  # Default fallback

    def calculate_team_projection(
        self,
        starters: List[str],
        projections: Dict[str, Dict],
        scoring_type: str = "pts_half_ppr",
    ) -> float:
        """
        Calculate total projected points for a team's starters.

        Args:
            starters: List of player IDs in the starting lineup.
            projections: Projection data from get_projections().
            scoring_type: One of 'pts_std', 'pts_half_ppr', 'pts_ppr'.

        Returns:
            Total projected points for the team.
        """
        total = 0.0
        missing_players = []

        for player_id in starters:
            if not player_id or player_id == "0":  # Empty roster slot
                continue

            player_proj = projections.get(player_id, {})
            points = player_proj.get(scoring_type, 0.0) or 0.0

            if points == 0.0:
                # Try defense variants (team defenses may have different IDs)
                defense_variants = [f"{player_id}_DEF", f"DEF_{player_id}"]
                for variant in defense_variants:
                    if variant in projections:
                        points = projections[variant].get(scoring_type, 0.0) or 0.0
                        break

                # Log missing projections (except for empty slots)
                if points == 0.0 and len(player_id) > 2:
                    missing_players.append(player_id)

            total += points

        if missing_players:
            logger.debug(f"No projections for {len(missing_players)} players")

        return round(total, 2)
