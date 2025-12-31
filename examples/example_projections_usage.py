"""
Example script demonstrating player projections features.

This script shows how to:
1. Fetch player projections from Sleeper
2. Calculate team projections
3. Get current NFL state
4. Detect league scoring type

Usage:
    python examples/example_projections_usage.py -u YOUR_USERNAME
"""
import argparse
from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
from sleeper_api.persistent_cache import PersistentCache


def main():
    """Main function to demonstrate projections features."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Demonstrate Sleeper API projections features"
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        required=True,
        help="Sleeper username"
    )
    args = parser.parse_args()

    # Initialize client and endpoints
    print("Initializing Sleeper API client...")
    client = SleeperClient(timeout=10, max_retries=3)
    user_endpoint = UserEndpoint(client)
    league_endpoint = LeagueEndpoint(client)
    persistent_cache = PersistentCache()
    projections_endpoint = ProjectionsEndpoint(client, persistent_cache)

    # Get user
    print(f"\nFetching user: {args.username}")
    user = user_endpoint.get_user(args.username)
    print(f"Found user: {user.display_name} (ID: {user.user_id})")

    # Get current NFL state
    print("\nFetching current NFL state...")
    nfl_state = league_endpoint.get_nfl_state(convert_results=True)
    print(f"Season: {nfl_state.season}, Week: {nfl_state.week}, Type: {nfl_state.season_type}")

    # Get user's leagues for current season
    season = nfl_state.season
    print(f"\nFetching leagues for {season}...")
    leagues = user_endpoint.get_leagues(user.user_id, 'nfl', season)

    if not leagues:
        print(f"No leagues found for {season}")
        return

    # Use the first league
    league = leagues[0]
    print(f"\nUsing league: {league.get('name')} (ID: {league.get('league_id')})")
    league_id = league.get('league_id')

    # Get league details
    league_model = league_endpoint.get_league_by_id(league_id)
    print(f"League: {league_model.name}")
    print(f"Teams: {league_model.total_rosters}")
    print(f"Roster positions: {league_model.roster_positions}")

    # Get player projections for current week
    print(f"\nFetching player projections for week {nfl_state.week}...")
    projections = projections_endpoint.get_projections(
        season=int(season),
        week=nfl_state.week
    )
    print(f"Loaded projections for {len(projections)} players")

    # Get scoring type for league
    scoring_type = projections_endpoint.get_scoring_type(league_id)
    print(f"League scoring type: {scoring_type}")

    # Get matchups for current week
    print(f"\nFetching matchups for week {nfl_state.week}...")
    matchups = league_endpoint.get_matchups(
        league_id,
        nfl_state.week,
        convert_results=True
    )

    # Calculate projections for each team
    print("\nTeam Projections:")
    print("-" * 60)
    for matchup in matchups:
        projected_points = projections_endpoint.calculate_team_projection(
            starters=matchup.starters,
            projections=projections,
            scoring_type=scoring_type
        )
        print(f"Roster {matchup.roster_id}:")
        print(f"  Current Points: {matchup.points:.2f}")
        print(f"  Projected Points: {projected_points:.2f}")

    # Show cache statistics
    print("\nCache Statistics:")
    stats = persistent_cache.get_stats()
    print(f"  Cached entries: {stats['entries']}")
    print(f"  Cache size: {stats['size_bytes']:,} bytes")
    print(f"  Cache directory: {stats['cache_dir']}")

    print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    main()
