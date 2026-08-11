"""
Example script demonstrating player projections features.

This script shows how to:
1. Fetch player projections from Sleeper
2. Calculate team projections
3. Get current NFL state
4. Detect league scoring type
5. Bulk-fetch multiple weeks concurrently (max_workers)
6. Track a single player's projections across weeks

Usage:
    python examples/example_projections_usage.py -u YOUR_USERNAME
"""
import argparse
import time
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

    # Get user's leagues. Leaving season out resolves "the current season"
    # from GET /state/nfl rather than the calendar year, and -- since
    # preseason weeks carry no league/projection data yet -- steps back to
    # the previous season automatically in that window (see the README's
    # "Season Defaults" section). A user with none in that season gets []
    # rather than an exception (see issue #21), so that's handled explicitly
    # rather than assuming leagues[0] exists.
    print("\nFetching leagues for the current season...")
    leagues = user_endpoint.fetch_nfl_leagues(user.user_id)
    if not leagues:
        print(f"No leagues found for {user.username}.")
        return

    # Use the first league. fetch_nfl_leagues returns LeagueModel objects, not
    # raw dicts, so these are attributes rather than .get() lookups. Read the
    # season back off it rather than recomputing the preseason fallback here
    # too -- it's needed again below for projections/matchups.
    league = leagues[0]
    season = int(league.season)
    print(f"\nUsing league: {league.name} (ID: {league.league_id}), season {season}")
    league_id = league.league_id

    # Get league details
    league_model = league_endpoint.get_league_by_id(league_id)
    print(f"League: {league_model.name}")
    print(f"Teams: {league_model.total_rosters}")
    print(f"Roster positions: {league_model.roster_positions}")

    # Get player projections for a week that actually has data. In preseason
    # the reported week is week 1 of a season that has not started, so the
    # fallback above pairs it with week 1 of the completed season.
    week = 1 if nfl_state.season_type == "pre" else int(nfl_state.week)
    print(f"\nFetching player projections for week {week}...")
    projections = projections_endpoint.get_projections(
        season=season,
        week=week
    )
    print(f"Loaded projections for {len(projections)} players")

    # Get scoring type for league
    scoring_type = projections_endpoint.get_scoring_type(league_id)
    print(f"League scoring type: {scoring_type}")

    # Get matchups for that week
    print(f"\nFetching matchups for week {week}...")
    matchups = league_endpoint.get_matchups(
        league_id,
        week,
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

    # Fetch several weeks at once, concurrently.
    #
    # get_season_projections() defaults to max_workers=1 (sequential). Passing a
    # higher value fans the weeks out over a thread pool, capped at 8. Results
    # and key order are identical either way -- only the timing differs.
    #
    # The gain depends on connection reuse: each worker needs its own pooled
    # connection, and a TLS handshake costs far more than a warm request. Over a
    # cold pool with only a couple of weeks the fan-out can be a wash. It pays
    # off with a long-lived client, more weeks, or higher round-trip latency.
    # The run below reuses the client above, so its pool is already warm.
    weeks_to_fetch = list(range(1, min(max(week, 6), 18) + 1))
    if len(weeks_to_fetch) > 1:
        print(f"\nBulk-fetching projections for weeks "
              f"{weeks_to_fetch[0]}-{weeks_to_fetch[-1]}...")
        start = time.perf_counter()
        season_projections = projections_endpoint.get_season_projections(
            season=season,
            weeks=weeks_to_fetch,
            max_workers=8
        )
        elapsed = time.perf_counter() - start

        populated = [w for w, data in season_projections.items() if data]
        print(f"  Fetched {len(populated)}/{len(weeks_to_fetch)} weeks "
              f"in {elapsed:.2f}s")
        # Weeks with no data come back as empty dicts rather than raising, so a
        # single bad week never takes down the rest of the batch.
        for fetched_week in weeks_to_fetch:
            count = len(season_projections[fetched_week])
            print(f"    Week {fetched_week:>2}: {count:>5,} players"
                  + ("" if count else "  (no data)"))

        # Track one player across every week fetched above. This reuses the
        # cache the bulk call just populated, so it costs no extra requests.
        # Pick the highest-projected player in the first populated week --
        # taking whichever id happens to come first usually lands on an
        # inactive player and prints a row of zeros.
        sample_player = None
        if populated:
            first_week = season_projections[populated[0]]
            sample_player = max(
                first_week,
                key=lambda pid: first_week[pid].get(scoring_type, 0.0) or 0.0,
            )
        if sample_player:
            tracked = projections_endpoint.get_player_season_projections(
                player_id=sample_player,
                season=season,
                weeks=weeks_to_fetch,
                max_workers=8
            )
            points = [
                f"W{w}:{proj.get(scoring_type, 0.0):.1f}"
                for w, proj in tracked.items() if proj
            ]
            print(f"\n  Player {sample_player} by week ({scoring_type}): "
                  f"{' '.join(points)}")

    # Show cache statistics
    print("\nCache Statistics:")
    stats = persistent_cache.get_stats()
    print(f"  Cached entries: {stats['entries']}")
    print(f"  Cache size: {stats['size_bytes']:,} bytes")
    print(f"  Cache directory: {stats['cache_dir']}")

    # Plain ASCII: Windows consoles default to cp1252, which cannot encode
    # emoji, and a UnicodeEncodeError here would fail the script on its last line.
    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
