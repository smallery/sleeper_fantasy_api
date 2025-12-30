# sleeper_fantasy_api

[![CI](https://github.com/smallery/sleeper_fantasy_api/workflows/CI/badge.svg)](https://github.com/smallery/sleeper_fantasy_api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/smallery/sleeper_fantasy_api/branch/main/graph/badge.svg)](https://codecov.io/gh/smallery/sleeper_fantasy_api)
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
- **Persistent Caching**: Two-tier caching system (in-memory + file-based) for expensive API calls
- **Retry Logic**: Exponential backoff for rate limits and network errors
- **Best Ball Support**: Optimal lineup calculator for Best Ball leagues
- **Variance Analysis**: Calculate historical scoring variance for teams
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

```python
from sleeper_api.endpoints.projections_endpoint import ProjectionsEndpoint
from sleeper_api.persistent_cache import PersistentCache

# Initialize projections endpoint with caching
persistent_cache = PersistentCache()
projections_endpoint = ProjectionsEndpoint(client, persistent_cache)

# Get current NFL state
nfl_state = league_endpoint.get_nfl_state(convert_results=True)
print(f"Season: {nfl_state.season}, Week: {nfl_state.week}")

# Fetch player projections for current week
projections = projections_endpoint.get_projections(
    season=int(nfl_state.season),
    week=nfl_state.week
)

# Detect league scoring type
scoring_type = projections_endpoint.get_scoring_type(league_id)

# Calculate team projection
matchups = league_endpoint.get_matchups(league_id, nfl_state.week, convert_results=True)
for matchup in matchups:
    projected = projections_endpoint.calculate_team_projection(
        starters=matchup.starters,
        projections=projections,
        scoring_type=scoring_type
    )
    print(f"Roster {matchup.roster_id}: {matchup.points:.1f} actual, {projected:.1f} projected")
```

### Advanced Usage: Best Ball Optimal Lineup

Calculate the optimal lineup for Best Ball leagues:

```python
from sleeper_api.endpoints.player_endpoint import PlayerEndpoint

# Get all players for position lookup
player_endpoint = PlayerEndpoint(client)
all_players = player_endpoint.get_all_players(sport='nfl', convert_results=False)

# Calculate optimal lineup
optimal_starters, optimal_total = projections_endpoint.calculate_optimal_lineup(
    roster_players=matchup.players,  # All players on roster
    projections=projections,
    roster_positions=league.roster_positions,
    all_players=all_players,
    scoring_type=scoring_type
)

print(f"Optimal lineup projects {optimal_total:.1f} points")
print(f"Optimal starters: {optimal_starters}")
```

### Advanced Usage: Team Variance Analysis

Analyze historical scoring variance for playoff odds:

```python
# Calculate variance through current week
variances = league_endpoint.calculate_team_variances(
    league_id=league_id,
    through_week=nfl_state.week - 1
)

for variance in variances:
    print(f"{variance.display_name}:")
    print(f"  Mean: {variance.mean:.1f}")
    print(f"  StdDev: {variance.stddev:.1f}")
    print(f"  Range: {variance.floor:.1f} - {variance.ceiling:.1f}")
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
  - **NEW**: `get_nfl_state()` - Get current NFL season/week information
  - **NEW**: `calculate_team_variances()` - Calculate historical scoring variance for all teams

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
    - `get_projections(season, week)` - Fetch all player projections for a specific week
    - `calculate_team_projection(starters, projections, scoring_type)` - Calculate total team projection
    - `get_scoring_type(league_id)` - Auto-detect league scoring format (PPR/Half-PPR/Standard)
    - `calculate_optimal_lineup()` - Calculate optimal lineup for Best Ball leagues
  - Uses persistent file caching (1-hour TTL) to minimize API calls
  - Supports PPR, Half-PPR, and Standard scoring formats

For more details, refer to the full [Sleeper API documentation](https://docs.sleeper.com/#introduction).

## Contributing

Contributions are welcome! We have comprehensive CI/CD in place to ensure code quality.

### Quick Start for Contributors

1. Fork the repository
2. Create a new branch (`git checkout -b githubUsername/feature-branch`)
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Make your changes and add tests
5. Run tests: `pytest --cov=sleeper_api`
6. Format code: `black sleeper_api tests examples`
7. Submit a pull request

### CI/CD Checks

All pull requests automatically run **5 efficient checks** in parallel:
- ✅ Tests on Python 3.10, 3.11, 3.12 (3 jobs)
- ✅ Code quality with flake8 (1 job)
- ✅ Import validation (1 job)
- ✅ Coverage reporting to Codecov
- ⚡ Fast execution with pip caching

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Contact
If you have any questions or issues, please contact [Sam Mallery](mailto:sleeperfantasyapi@gmail.com).
