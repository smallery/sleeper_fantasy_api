"""
This module provides the `ProjectionsEndpoint` class for interacting
with player projections from the Sleeper API.

Note: This uses an undocumented Sleeper endpoint that may change.
"""
import logging
from typing import Dict, List, Optional
from ..persistent_cache import PersistentCache
from ..exceptions import SleeperAPIError

logger = logging.getLogger(__name__)

# NFL regular season has 18 weeks
NFL_REGULAR_SEASON_WEEKS = 18


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

    def get_projections(self, season: int, week: int) -> Dict[str, Dict]:
        """
        Fetch all player projections for a specific week.

        Uses an undocumented Sleeper endpoint to get projected stats.
        Results are cached in persistent file storage to minimize API calls.

        Args:
            season: NFL season year (e.g., 2024).
            week: Week number (1-18).

        Returns:
            Dict mapping player_id -> projection stats including:
            - pts_std: Standard scoring projected points
            - pts_half_ppr: Half-PPR projected points
            - pts_ppr: Full PPR projected points
            - Individual stat projections (passing_yards, rushing_yards, etc.)

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
        """
        cache_key = f"projections:{season}:{week}"

        # Check persistent file cache
        cached = self.persistent_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Loaded projections from cache for {season} week {week}")
            return cached

        # Fetch from API
        try:
            endpoint = f"projections/nfl/regular/{season}/{week}"
            data = self.client.get(endpoint)

            if data:
                # Cache for 24 hours
                self.persistent_cache.set(cache_key, data, ttl_hours=24.0)
                logger.info(f"Fetched projections for {season} week {week}")
                return data
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
        week: int
    ) -> Optional[Dict]:
        """
        Fetch projection data for a single player.

        This is a convenience method that fetches all projections for the week
        (using cache) and returns just the specified player's data.

        Args:
            player_id: Sleeper player ID.
            season: NFL season year (e.g., 2024).
            week: Week number (1-18).

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
        projections = self.get_projections(season, week)
        return projections.get(player_id)

    def get_season_projections(
        self,
        season: int,
        weeks: Optional[List[int]] = None
    ) -> Dict[int, Dict[str, Dict]]:
        """
        Fetch player projections for multiple weeks in a season.

        This is a convenience method for bulk-fetching projection data.
        Each week's data is fetched separately and cached independently.

        Args:
            season: NFL season year (e.g., 2024).
            weeks: List of week numbers to fetch. If None, fetches all 18 regular season weeks.

        Returns:
            Dict mapping week number -> projections dict.
            Example: {1: {"player1": {...}}, 2: {"player1": {...}}, ...}

        Note:
            - Weeks with no data available return empty dicts
            - Each week is cached independently (24-hour TTL)
            - Failed weeks are logged but don't stop other weeks from fetching

        Example:
            >>> # Fetch first 4 weeks
            >>> projections = endpoint.get_season_projections(2024, weeks=[1, 2, 3, 4])
            >>> week_1 = projections[1]
            >>>
            >>> # Fetch entire season
            >>> all_projections = endpoint.get_season_projections(2024)
        """
        if weeks is None:
            weeks = list(range(1, NFL_REGULAR_SEASON_WEEKS + 1))

        season_data = {}
        for week in weeks:
            try:
                projections = self.get_projections(season, week)
                season_data[week] = projections
                if projections:
                    logger.debug(f"Fetched {len(projections)} players for week {week}")
                else:
                    logger.warning(f"No projection data for week {week}")
            except Exception as e:
                logger.error(f"Failed to fetch projections for week {week}: {e}")
                season_data[week] = {}

        return season_data

    def get_player_season_projections(
        self,
        player_id: str,
        season: int,
        weeks: Optional[List[int]] = None
    ) -> Dict[int, Optional[Dict]]:
        """
        Fetch projections for a single player across multiple weeks.

        This is a convenience method for tracking one player's projections
        over time. Uses cached data from get_season_projections().

        Args:
            player_id: Sleeper player ID.
            season: NFL season year (e.g., 2024).
            weeks: List of week numbers to fetch. If None, fetches all 18 weeks.

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
        season_data = self.get_season_projections(season, weeks)

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
