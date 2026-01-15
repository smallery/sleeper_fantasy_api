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
- Python 3.10

### Installation:
```bash
git clone https://github.com/smallery/sleeper_fantasy_api.git
cd sleeper_fantasy_api
pip install -r requirements.txt
```

## Usage

### Basic Usage

Get started with simple user and league queries:

```python
from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint

# Initialize client
client = SleeperClient()
user_endpoint = UserEndpoint(client)
league_endpoint = LeagueEndpoint(client)

# Get user
user = user_endpoint.get_user("your_username")
print(f"User: {user.display_name}")

# Get user's leagues for 2024
leagues = user_endpoint.get_leagues(user.user_id, 'nfl', '2024')

# Get league details
league = league_endpoint.get_league_by_id(leagues[0]['league_id'])
print(f"League: {league.name}")
```

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
    - `get_season_projections(season, weeks=None)` - Bulk fetch projections across multiple weeks (or all 18 weeks)
    - `get_player_season_projections(player_id, season, weeks=None)` - Track one player across multiple weeks
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

All PRs automatically run tests on Python 3.10, 3.11, and 3.12.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Contact
If you have any questions or issues, please contact [Sam Mallery](mailto:sleeperfantasyapi@gmail.com).
