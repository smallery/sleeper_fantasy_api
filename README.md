# sleeper_fantasy_api

[![CI](https://github.com/smallery/sleeper_fantasy_api/workflows/CI/badge.svg)](https://github.com/smallery/sleeper_fantasy_api/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An object-oriented Python wrapper for the [Sleeper Fantasy Football API](https://docs.sleeper.com/), designed to simplify working with data on users, leagues, transactions, and more.

The Sleeper API is currently read-only.

H/T to other repos who created similar functions before me:
- [sleeper-api-wrapper](https://github.com/dtsong/sleeper-api-wrapper)
- [sleeper-py](https://github.com/AdamCurtisVT/sleeper-py)

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Error Handling](#error-handling)
  - [Season Defaults: How "Current Season" Is Resolved](#season-defaults-how-current-season-is-resolved)
- [Endpoints](#endpoints)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview
This project simplifies accessing the Sleeper API, allowing users to easily fetch player stats, league data, transactions, and more in an object-oriented manner. The wrapper supports complex queries using `AND` and `OR` logic, with a focus on easy integration and flexibility.

## Features

### Core Features
- Fetching player stats, leagues, and transactions
- Supports advanced player search logic (e.g., `AND`/`OR` conditions)
- Object-oriented design for ease of use and integration
- Comprehensive error handling with specific exception types

### Advanced Features (New!)
- **Player Projections**: Access weekly player projections (undocumented Sleeper API endpoint)
- **NFL Data**: Team depth charts and historical schedules (undocumented Sleeper API endpoints)
- **Complete League Data**: One-call convenience method to fetch league, rosters, and users together
- **Persistent Caching**: File-based caching system for expensive API calls
- **Retry Logic**: Exponential backoff for rate limits and network errors
- **NFL State**: Get current NFL season, week, and game state
- **Scoring Type Detection**: Automatically detect PPR/Half-PPR/Standard scoring

### Planned Features
- Custom setting of CONVERT_RESULT global variable by user

## Installation
To install locally, follow these steps:

### Prerequisites:
- Python 3.10+

### Installation:
```bash
pip install sleeper_fantasy_api
```

### From source (for development):
```bash
git clone https://github.com/smallery/sleeper_fantasy_api.git
cd sleeper_fantasy_api
pip install -e ".[dev]"
```

## Usage

### Basic Usage

Get started with simple user and league queries:

```python
from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.exceptions import UserNotFoundError

# Initialize client
client = SleeperClient()
user_endpoint = UserEndpoint(client)
league_endpoint = LeagueEndpoint(client)

# Get user. Raises UserNotFoundError if the username/user_id doesn't exist --
# see "Error Handling" below.
try:
    user = user_endpoint.get_user("your_username")
except UserNotFoundError:
    print("No such user")
else:
    print(f"User: {user.display_name}")

    # Get user's leagues for 2024. Pass no season to use the current one
    # instead (resolved from the live NFL state, not the calendar year --
    # see "Error Handling" below). Returns [] if the user has none.
    leagues = user_endpoint.fetch_nfl_leagues(user.user_id, 2024)

    if leagues:
        # Get league details. fetch_nfl_leagues returns LeagueModel objects,
        # so these are attributes rather than dict lookups.
        league = league_endpoint.get_league_by_id(leagues[0].league_id)
        print(f"League: {league.name}")
```

### Error Handling

All exceptions this package raises are exported from the package root:

```python
from sleeper_api import SleeperAPIError, UserNotFoundError, LeagueNotFoundError, RateLimitError
```

- **`SleeperAPIError`** -- base class for everything below; also raised
  directly for non-404 HTTP errors and malformed responses.
- **`UserNotFoundError`** / **`LeagueNotFoundError`** -- raised by
  `get_user()` and `get_league_by_id()` when the given username/user_id or
  league_id doesn't exist. Both are `SleeperAPIError` subclasses, so
  catching the base type still works.
- **`RateLimitError`** -- raised when Sleeper rate-limits the client (429)
  after retries are exhausted.

Not every missing resource raises, though. A 404 from Sleeper is only ever
*absence*, not failure -- `SleeperClient` returns `None` for it either way.
Whether an endpoint method turns that `None` into an exception depends on
what was asked for:

- **Looked up by name/ID** (a specific user, a specific league): the caller
  asked about a resource that should exist, so a miss is an error --
  `get_user()` and `get_league_by_id()` raise.
- **A resource that's normal to have none of** (a user's leagues for a
  season, a league's matchups for a week): an empty result is expected, not
  exceptional -- `fetch_nfl_leagues()` returns `[]`, `get_matchups()` returns
  `None`/`[]`. No exception to catch.

Each endpoint method's docstring says explicitly which behavior it uses.

### Season Defaults: How "Current Season" Is Resolved

`fetch_nfl_leagues()`, `get_all_drafts()`, and `get_drafts_by_user()` accept
an optional `season`; leaving it out resolves "the current season" from
`GET /state/nfl` (Sleeper's own authoritative source) via
`sleeper_api.config.get_current_season()`, rather than
`datetime.now().year` -- a season is labelled by the year it *starts*, so the
calendar year overshoots by one from January through roughly August. The
resolved value is cached briefly (about an hour), not frozen once per
process, so a long-running service picks up a season rollover without a
restart.

**Preseason behavior is not one rule -- it depends on what the method is
for.** While Sleeper reports `season_type == "pre"`, `/state/nfl` names the
*upcoming* season -- the one about to be played, which has no completed-season
data yet but is exactly when that season's drafts happen:

- **`fetch_nfl_leagues()`** defaults to the *previous* season during
  preseason -- the upcoming season usually has no league data yet. This is
  a default only: an explicit `season=<the season /state/nfl just
  reported>` is always accepted (leagues for it can exist as soon as
  they're created); only the unspecified-`season` case prefers last year.
- **`get_all_drafts()` / `get_drafts_by_user()`** default to the *upcoming*
  season during preseason -- unlike leagues, a season's draft happens
  during that season's own preseason window, so "the current season" for a
  draft lookup means the one about to be played. Defaulting these to the
  previous season would silently return last year's drafts, which usually
  exist and so look like a valid (but wrong) answer.

If you want the opposite of a given method's default, pass `season`
explicitly -- `get_current_season(client, prefer_previous_during_preseason=...)`
is also usable directly if you're building similar logic of your own.

### Client Lifecycle: Context Manager vs. Long-Lived Client

`SleeperClient` owns a `requests.Session`, which owns a connection pool.
Nothing closes that automatically on a predictable schedule -- in CPython it
happens whenever the garbage collector gets around to it, which can be
arbitrarily late once the client is captured by a closure or held as a
module-level singleton. There are two supported patterns, and which one you
want depends on how long the client sticks around:

**Short-lived usage (scripts, one-off calls, tests): use it as a context
manager.** This guarantees the session -- and its sockets -- are released as
soon as you're done, even if an exception is raised inside the block.

```python
from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint

with SleeperClient() as client:
    user = UserEndpoint(client).get_user("your_username")
    print(f"User: {user.display_name}")
# session and connection pool are closed here, deterministically
```

**Long-lived usage (a service, a web app, anything that makes many calls over
its lifetime): create one client and hold it for as long as the app runs,
then call `close()` on shutdown.** Do *not* wrap every call in `with` here --
a fresh `SleeperClient()` per request throws away the connection pool each
time, and a TLS handshake to Sleeper costs roughly 0.3s versus roughly 0.03s
for a request that reuses a warm connection. This is also why
`get_season_projections(max_workers=...)` (see below) is fast: it depends on
a pool of already-open connections to fan out across, not on opening a new
one per request.

```python
# module-level singleton, or held on an app/service object -- either way,
# constructed once and reused across many requests
client = SleeperClient()

def handle_request(username):
    return UserEndpoint(client).get_user(username)

# on application shutdown:
client.close()
```

Calling a method on a closed client raises `RuntimeError` rather than
silently reopening a connection -- `requests.Session` does not itself refuse
reuse after `close()`, so this client checks explicitly to keep the lifecycle
honest. `close()` itself is idempotent; calling it more than once is safe.

### Calling This Client from Async Code

`SleeperClient` is built on `requests` and is synchronous end to end -- every
method blocks the calling thread until the HTTP response comes back. That's
fine from a script or a sync web framework, but if you call it directly from
inside an event loop (FastAPI, aiohttp, discord.py, an `asyncio` task) it
blocks the *entire loop* for the duration of the call, not just the coroutine
that made it. For a single user lookup that's tens of milliseconds. For
`get_season_projections()` fetching a full season, it's the better part of a
second -- long enough to stall every other request or event your app is
handling concurrently.

**The pattern: `asyncio.to_thread`.** It runs a blocking call in a worker
thread and hands you back an awaitable, so the loop stays free to do other
work while the request is in flight.

```python
import asyncio
from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint

async def get_user(client: SleeperClient, username: str):
    user_endpoint = UserEndpoint(client)
    # runs client.get(...) in a worker thread; the event loop is free
    # for the entire duration of the request
    return await asyncio.to_thread(user_endpoint.get_user, username)

async def main():
    # `with` guarantees the session is released even if the request raises --
    # on an exceptional exit a bare client.close() at the end would be skipped.
    # See the cancellation caveat below before using this shape in a service.
    with SleeperClient() as client:
        user = await get_user(client, "your_username")
        print(f"User: {user.display_name}")

asyncio.run(main())
```

**Cancellation caveat: don't close a client out from under a running worker.**
Cancelling an `await asyncio.to_thread(...)` — via `asyncio.wait_for`, a
timeout, or task cancellation — abandons the *awaitable*, but it cannot stop
the worker thread, which keeps running the request to completion. If that
cancellation also unwinds a `with SleeperClient()` block, the client is closed
while the worker is still using it. A *new* request from that worker fails
fast with `RuntimeError` (the closed-client guard), which is noisy but safe.
A request already inside its retry loop is the sharper case: the closed check
runs when a request starts, not between retries, so it can open a fresh
connection *after* `close()`.

The `with` form above is fine for a script that runs to completion, which is
the common case and why it's shown first. But **if anything in your program can
cancel or time out these calls, use a long-lived client** whose shutdown cannot
race outstanding work — hold it for the life of the process and close it once,
during orderly shutdown, as in the FastAPI example below.

If you must scope a client narrowly under cancellation, the block has to wait
for the worker itself. Note that `asyncio.shield` alone does **not** do this:
it keeps the inner task from being cancelled, but the `await` on it still
raises `CancelledError` immediately, so the `with` block unwinds anyway and
closes the client while the worker runs on. You have to catch the cancellation
and await the task before re-raising:

```python
task = asyncio.create_task(get_user(client, "your_username"))
try:
    user = await asyncio.shield(task)
except asyncio.CancelledError:
    await task          # let the worker finish before the client is closed
    raise
```

`asyncio.to_thread` requires Python 3.9+; since this package requires
3.10+, prefer it over the older, more verbose
`loop.run_in_executor(None, func, *args)` -- they do the same thing, but
`run_in_executor` predates `to_thread` and only exists for callers still
supporting Python 3.8 or earlier.

**Wrapping the existing thread-pool fan-out.** `get_season_projections(max_workers=...)`
(see [Advanced Usage: Player Projections](#advanced-usage-player-projections)
below) already fans requests out across a `ThreadPoolExecutor` internally.
Wrapping that whole call in `asyncio.to_thread` is fine and is the
recommended way to call it from async code -- it just moves the entire
fan-out onto one worker thread, off the event loop:

```python
season_projections = await asyncio.to_thread(
    projections_endpoint.get_season_projections,
    season=2025,
    weeks=list(range(1, 19)),
    max_workers=8,
)
```

Don't try to be cleverer than that by running individual weeks through your
own `asyncio.to_thread` calls to parallelize on top of the library's thread
pool -- `get_season_projections` already owns a pool of up to 8 threads
internally, and stacking a second pool of coroutines-that-spawn-threads
around it just adds scheduling overhead for no extra concurrency. Call it
once, wrapped once.

**Client lifetime still applies.** The same long-lived-client guidance from
[Client Lifecycle](#client-lifecycle-context-manager-vs-long-lived-client)
above holds in an async app: create one `SleeperClient` when your app starts
(e.g. held on the FastAPI `app.state` or equivalent), reuse it across
requests, and `close()` it on shutdown. The warm connection pool it holds is
what makes the thread-pool fan-out fast in the first place; a fresh client
per request throws that away regardless of whether the call is wrapped in
`asyncio.to_thread`.

A complete FastAPI application, using a lifespan handler to build the client
once at startup and close it at shutdown:

```python
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One client for the life of the process, so the connection pool stays warm.
    app.state.sleeper = SleeperClient()
    yield
    app.state.sleeper.close()


# The lifespan handler only runs if it is registered here.
app = FastAPI(lifespan=lifespan)


@app.get("/user/{username}")
async def get_user(username: str, request: Request):
    user_endpoint = UserEndpoint(request.app.state.sleeper)
    user = await asyncio.to_thread(user_endpoint.get_user, username)
    return {"display_name": user.display_name}
```

**Why there's no native async client (yet).** This library does not ship an
`asyncio`-native client (no `httpx`/`aiohttp`, no `AsyncSleeperClient`).
Measured against the live API, 18 weeks of 2025 projections:

| | time |
|---|---|
| sequential | ~0.83s |
| 8 threads (`max_workers=8`) | ~0.35s |
| network portion alone | ~3.4x parallelizable |

The existing thread-pool fan-out already captures most of the available
concurrency for this workload; the residual gap is GIL-bound JSON
serialization, which a native async client would not help with either. In
other words, **`asyncio.to_thread` will not make requests faster than
calling this client directly** -- it makes them not block your event loop
while they happen, which is a different and, for most callers, more
relevant problem. If you outgrow this pattern -- e.g. you need thousands of
truly concurrent connections rather than freedom from blocking a handful of
requests -- see [issue #23](https://github.com/smallery/sleeper_fantasy_api/issues/23)
for the tracked discussion of a native async client, and weigh in there if
that's you.

### Advanced Usage: Player Projections

Access weekly player projections and calculate team totals:

**Important**:
- **Projections** (this endpoint) = Pre-game predictions for ALL players
- **Actuals** (matchups endpoint) = Post-game results for ROSTERED players only in a specific league
- For league-agnostic actual stats, use external APIs (ESPN, NFL.com, etc.)

```python
from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
from sleeper_api.persistent_cache import PersistentCache

# Initialize projections endpoint with caching
persistent_cache = PersistentCache()
projections_endpoint = ProjectionsEndpoint(client, persistent_cache)

# Get current NFL state
nfl_state = league_endpoint.get_nfl_state(convert_results=True)
print(f"Season: {nfl_state.season}, Week: {nfl_state.week}")

# Option 1: Fetch all player projections for one week (cached for 24 hours)
projections = projections_endpoint.get_projections(
    season=int(nfl_state.season),
    week=nfl_state.week
)
# Returns ALL projection data from Sleeper API
# Includes: pts_ppr, pts_half_ppr, pts_std, pass_yd, rush_yd, rec, etc.
# NOTE: These are PROJECTIONS (predictions), not actuals

# Option 2: Get projection for a single player (uses cache)
player_proj = projections_endpoint.get_player_projection(
    player_id="4018",  # Patrick Mahomes
    season=int(nfl_state.season),
    week=nfl_state.week
)
if player_proj:
    print(f"Projected PPR Points: {player_proj.get('pts_ppr')}")
    print(f"Projected Passing Yards: {player_proj.get('pass_yd')}")
    print(f"Projected Pass TDs: {player_proj.get('pass_td')}")

# Option 3: Bulk fetch projections for multiple weeks
season_projections = projections_endpoint.get_season_projections(
    season=2024,
    weeks=[1, 2, 3, 4]  # Or None for all 18 weeks
)
# Returns: {1: {players...}, 2: {players...}, 3: {players...}, 4: {players...}}

# Pass max_workers to fetch the weeks concurrently (capped at 8) -- same
# results, same key order. Measured on the live API, 18 weeks of the 2025
# season over a warm connection: ~0.8s sequential vs ~0.35s with 8 workers.
# The gain depends on connection reuse -- see the method docstring; over a
# cold connection pool with only a few weeks it can be a wash.
rest_of_season = projections_endpoint.get_season_projections(
    season=2024,
    weeks=list(range(10, 19)),
    max_workers=8
)

# Option 4: Track one player across multiple weeks
mahomes_season = projections_endpoint.get_player_season_projections(
    player_id="4018",
    season=2024,
    weeks=[1, 2, 3, 4]  # Or None for all 18 weeks
)
for week, proj in mahomes_season.items():
    if proj:
        print(f"Week {week}: {proj.get('pts_ppr')} projected PPR points")

# Get actual points scored (after games are played)
matchups = league_endpoint.get_matchups(league_id, nfl_state.week, convert_results=True)
for matchup in matchups:
    print(f"Roster {matchup.roster_id}: {matchup.points:.1f} actual points scored")

# Compare projections vs actuals
scoring_type = projections_endpoint.get_scoring_type(league_id)
for matchup in matchups:
    projected = projections_endpoint.calculate_team_projection(
        starters=matchup.starters,
        projections=projections,
        scoring_type=scoring_type
    )
    actual = matchup.points
    diff = actual - projected
    print(f"Roster {matchup.roster_id}: {actual:.1f} actual vs {projected:.1f} projected (diff: {diff:+.1f})")
```

### NFL Data: Team Depth Charts & Schedules

Access NFL team depth charts and historical schedules:

```python
from sleeper_api import SleeperClient, NFLEndpoint

client = SleeperClient()
nfl_endpoint = NFLEndpoint(client)

# Get team depth chart
depth_chart = nfl_endpoint.get_team_depth_chart('SF')
print(f"49ers Starting QB: {depth_chart.qb[0]}")  # First QB in depth chart
print(f"All RBs: {depth_chart.rb}")  # All RBs in depth order

# Get all starters
starters = depth_chart.get_starters()
print(f"Starting QB: {starters['QB']}")
print(f"Starting RBs: {starters['RB']}")

# Get NFL schedule (supports 2009-present)
schedule = nfl_endpoint.get_schedule(2024, postseason=False)
print(f"Total games in 2024: {len(schedule.games)}")

# Get games for a specific week
week_1_games = schedule.get_games_by_week(1)
for game in week_1_games:
    print(f"Week {game.week}: {game.away} @ {game.home} ({game.date})")

# Get all games for a specific team
sf_games = schedule.get_games_by_team('SF')
print(f"49ers have {len(sf_games)} games this season")

# Get postseason schedule
playoffs = nfl_endpoint.get_postseason_schedule(2024)
print(f"Playoff games: {len(playoffs.games)}")
```

### Complete League Data (Convenience Method)

Fetch league, rosters, and users in a single call:

```python
from sleeper_api import SleeperClient, LeagueEndpoint

client = SleeperClient()
league_endpoint = LeagueEndpoint(client)

# Get everything at once
data = league_endpoint.get_complete_league_data('123456789')

# Access league info
league = data['league']
print(f"League: {league.name} ({league.season})")
print(f"Status: {league.status}")

# Access rosters
rosters = data['rosters']
print(f"Teams: {len(rosters)}")

# Access users
users = data['users']
for user in users:
    print(f"User: {user.display_name}")

# Quick roster-to-user lookup
roster_to_user = data['roster_to_user']
owner_id = roster_to_user[1]  # Get owner of roster 1
owner = next(u for u in users if u.user_id == owner_id)
print(f"Roster 1 owner: {owner.display_name}")
```

### Example Scripts

Run the included example scripts from the command line:

**Basic usage** - Get user info:
```bash
python3 examples/example_basic_usage.py -u [YOUR_USERNAME]
```

**Advanced usage** - Gather user, league, draft, and player data:
```bash
python3 examples/example_advanced_usage.py -u [YOUR_USERNAME]
```

**Player search** - Access the player database with complex queries:
```bash
python3 examples/example_player_endpoint_search_queries.py
```

**Projections** - Demonstrate player projections and advanced features:
```bash
python3 examples/example_projections_usage.py -u [YOUR_USERNAME]
```

## Endpoints

The current endpoints available through the API are the following:

### Core Endpoints

- **User Endpoint**:
  - `user_endpoint`: Retrieve information about a user using their username or user_id
  - Get user leagues for a specific season

- **League Endpoint**:
  - `league_endpoint`: Retrieve information on leagues with a given league_id
  - Get rosters, users, matchups, brackets, transactions, and traded picks
  - **NEW**: `get_complete_league_data(league_id)` - Fetch league, rosters, and users in one call
  - **NEW**: `get_nfl_state()` - Get current NFL season/week information

- **Player Endpoint**:
  - `player_endpoint`: Retrieve the database of players from Sleeper along with key attributes
  - Built-in caching to store player data locally (24-hour cache)
  - Search players with complex AND/OR logic
  - Get trending players (adds/drops)

- **Draft Endpoint**:
  - `draft_endpoint`: Retrieve information about a draft (picks, users, trades) with a given draft_id

### Advanced Endpoints (New!)

- **Projections Endpoint**:
  - `projections_endpoint`: Access weekly player projections from Sleeper
  - **Methods**:
    - `get_projections(season, week)` - Fetch all player projections for one week
    - `get_player_projection(player_id, season, week)` - Fetch single player projection for one week
    - `get_season_projections(season, weeks=None, max_workers=1)` - Bulk fetch projections across multiple weeks (or all 18 weeks); `max_workers > 1` fetches weeks concurrently
    - `get_player_season_projections(player_id, season, weeks=None, max_workers=1)` - Track one player across multiple weeks
    - `calculate_team_projection(starters, projections, scoring_type)` - Calculate total team projection
    - `get_scoring_type(league_id)` - Auto-detect league scoring format (PPR/Half-PPR/Standard)
  - Returns complete projection data: pts_ppr, pts_half_ppr, pts_std, plus individual stats (pass_yd, rush_yd, rec, etc.)
  - Uses persistent file caching (24-hour TTL) to minimize API calls

- **NFL Endpoint**:
  - `nfl_endpoint`: Access NFL-specific data (undocumented Sleeper API endpoints)
  - **Methods**:
    - `get_team_depth_chart(team)` - Fetch current depth chart for any NFL team
    - `get_schedule(year, postseason=False)` - Get NFL schedule (regular season or playoffs, 2009-present)
    - `get_regular_season_schedule(year)` - Convenience method for regular season
    - `get_postseason_schedule(year)` - Convenience method for playoffs
  - Returns models with helper methods: `get_games_by_week()`, `get_games_by_team()`, `get_starters()`
  - Note: These endpoints are undocumented and may change without notice

For more details, refer to the full [Sleeper API documentation](https://docs.sleeper.com/#introduction).

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a new branch: `git checkout -b yourname/feature-name`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Format code: `flake8 sleeper_api`
6. Submit a pull request

All PRs automatically run tests on Python 3.10, 3.11, 3.12, and 3.13.

## Releasing

Releases publish to PyPI automatically on a version tag, via
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — there is
no API token stored in this repo or on any developer machine.

1. Bump `version` in `pyproject.toml` **and** `__version__` in
   `sleeper_api/__init__.py` (the workflow refuses to publish if the tag
   disagrees with either).
2. Add the release notes to `CHANGELOG.md`.
3. Merge to `main`, then tag and push:

```bash
git tag v0.5.0 && git push origin v0.5.0
```

`.github/workflows/publish.yml` then runs the test suite, builds the sdist and
wheel, and uploads them.

### A note on dependency pinning

Runtime dependencies in `pyproject.toml` are declared as **ranges, never `==`
pins**. pip applies a library's constraints to the consuming application's
entire dependency resolution, so an exact pin here becomes an exact pin for
everyone who installs this package — they cannot patch a CVE in a transitive
dependency, and there is nothing they can do about it but wait for a new
release. Applications pin; libraries constrain. Test-only tools belong in the
`dev` extra, not in `[project.dependencies]`.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Contact
If you have any questions or issues, please contact [Sam Mallery](mailto:sleeperfantasyapi@gmail.com).
