"""
This module provides the `ProjectionsEndpoint` class for interacting
with player projections from the Sleeper API.

Note: This uses an undocumented Sleeper endpoint that may change.
"""
import logging
from typing import Dict, Any, List, Optional
from ..persistent_cache import PersistentCache
from ..exceptions import SleeperAPIError

logger = logging.getLogger(__name__)


class ProjectionsEndpoint:
    """
    Projections endpoint class to fetch player projections.

    Uses an undocumented Sleeper endpoint to get projected points.
    Results are cached in both memory and persistent file storage
    to minimize API calls.
    """

    # Position eligibility for different roster slots
    SLOT_ELIGIBLE: Dict[str, List[str]] = {
        "QB": ["QB"],
        "RB": ["RB"],
        "WR": ["WR"],
        "TE": ["TE"],
        "K": ["K"],
        "DEF": ["DEF"],
        "FLEX": ["RB", "WR", "TE"],
        "SUPER_FLEX": ["QB", "RB", "WR", "TE"],
        "REC_FLEX": ["WR", "TE"],
        "WRRB_FLEX": ["WR", "RB"],
        "IDP_FLEX": ["DL", "LB", "DB"],
    }

    def __init__(self, client, persistent_cache: Optional[PersistentCache] = None):
        """
        Initialize the projections endpoint.

        Args:
            client: SleeperClient instance.
            persistent_cache: Optional PersistentCache instance for caching projections.
        """
        self.client = client
        self.persistent_cache = persistent_cache or PersistentCache(default_ttl_hours=1.0)

    def get_projections(self, season: int, week: int) -> Dict[str, Dict]:
        """
        Fetch player projections for a specific week.

        Uses an undocumented Sleeper endpoint to get projected points.
        Results are cached in persistent file storage to minimize API calls.

        Args:
            season: NFL season year (e.g., 2024).
            week: Week number (1-18).

        Returns:
            Dict mapping player_id -> projection stats including:
            - pts_std: Standard scoring projected points
            - pts_half_ppr: Half-PPR projected points
            - pts_ppr: Full PPR projected points

        Note:
            This uses an undocumented Sleeper endpoint that may change.
            Returns empty dict on failure for graceful degradation.
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
                # Cache for 1 hour
                self.persistent_cache.set(cache_key, data, ttl_hours=1.0)
                logger.info(f"Fetched projections for {season} week {week}")
                return data
            else:
                logger.warning(f"No projection data returned for {season} week {week}")
                return {}

        except SleeperAPIError as e:
            logger.warning(f"Failed to fetch projections: {e}")
            return {}  # Graceful degradation

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

    def get_player_position(self, player_id: str, all_players: Dict[str, Dict]) -> Optional[str]:
        """
        Get position for a player ID.

        Args:
            player_id: The Sleeper player ID.
            all_players: Dictionary of all players from get_all_players().

        Returns:
            Position string (QB, RB, WR, TE, K, DEF) or None if not found.
        """
        if not player_id or player_id == "0":
            return None

        # Defense IDs are 2-3 letter team codes (e.g., 'SF', 'NYG')
        if len(player_id) <= 3 and player_id.isalpha():
            return "DEF"

        # Regular players
        player = all_players.get(player_id, {})
        return player.get("position")

    def calculate_optimal_lineup(
        self,
        roster_players: List[str],
        projections: Dict[str, Dict],
        roster_positions: List[str],
        all_players: Dict[str, Dict],
        scoring_type: str = "pts_ppr",
    ) -> tuple[List[str], float]:
        """
        Calculate optimal projected lineup for Best Ball.

        Uses a greedy algorithm to fill roster slots with the highest
        projected players. Handles standard positions and flex slots.

        Args:
            roster_players: All player IDs on the roster.
            projections: Projection data from get_projections().
            roster_positions: League roster positions (e.g., ['QB', 'RB', 'RB', ...]).
            all_players: Dictionary of all players for position lookup.
            scoring_type: Scoring type ('pts_std', 'pts_half_ppr', 'pts_ppr').

        Returns:
            Tuple of (optimal_starters list, total_projected_points).
        """
        # Build player data with positions and projections
        player_data = []
        for pid in roster_players:
            if not pid or pid == "0":
                continue

            position = self.get_player_position(pid, all_players)
            pts = projections.get(pid, {}).get(scoring_type, 0) or 0

            player_data.append({
                "id": pid,
                "position": position,
                "pts": pts,
            })

        # Sort by projection descending
        player_data.sort(key=lambda x: x["pts"], reverse=True)

        # Get starter slots (exclude BN and IR)
        starter_slots = [pos for pos in roster_positions if pos not in ("BN", "IR")]

        # Fill standard positions first (QB, RB, WR, TE, K, DEF), then flex
        # This ensures we don't waste a RB on FLEX when we need 2 RBs
        standard_slots = [s for s in starter_slots if s in ("QB", "RB", "WR", "TE", "K", "DEF")]
        flex_slots = [s for s in starter_slots if s not in standard_slots]

        used_players: set = set()
        optimal_starters: List[str] = []
        total_pts = 0.0

        # Fill standard slots
        for slot in standard_slots:
            eligible_positions = self.SLOT_ELIGIBLE.get(slot, [slot])
            best_player = None

            for player in player_data:
                if player["id"] in used_players:
                    continue
                if player["position"] in eligible_positions:
                    best_player = player
                    break

            if best_player:
                optimal_starters.append(best_player["id"])
                used_players.add(best_player["id"])
                total_pts += best_player["pts"]
            else:
                optimal_starters.append("")  # Empty slot

        # Fill flex slots with remaining best players
        for slot in flex_slots:
            eligible_positions = self.SLOT_ELIGIBLE.get(slot, [slot])
            best_player = None

            for player in player_data:
                if player["id"] in used_players:
                    continue
                if player["position"] in eligible_positions:
                    best_player = player
                    break

            if best_player:
                optimal_starters.append(best_player["id"])
                used_players.add(best_player["id"])
                total_pts += best_player["pts"]
            else:
                optimal_starters.append("")  # Empty slot

        return optimal_starters, round(total_pts, 2)
