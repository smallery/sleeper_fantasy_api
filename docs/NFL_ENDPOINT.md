# NFLEndpoint Documentation

Complete API reference for the NFLEndpoint class.

## Overview

The `NFLEndpoint` provides access to NFL-specific data through undocumented Sleeper API endpoints. These endpoints allow you to fetch team depth charts and historical NFL schedules.

**⚠️ Important**: These are undocumented Sleeper API endpoints and may change without notice. Always handle potential API errors gracefully.

## Installation & Setup

```python
from sleeper_api import SleeperClient, NFLEndpoint

# Initialize client and endpoint
client = SleeperClient()
nfl_endpoint = NFLEndpoint(client)
```

## Methods

### get_team_depth_chart()

Fetch the current depth chart for an NFL team.

**Signature:**
```python
def get_team_depth_chart(
    team: str,
    convert_results: bool = True
) -> Union[TeamDepthChartModel, dict]
```

**Parameters:**
- `team` (str): NFL team abbreviation (e.g., 'SF', 'KC', 'GB', 'NE')
  - Case-insensitive (automatically converted to uppercase)
  - Must be valid NFL team abbreviation
- `convert_results` (bool, optional): If True, returns TeamDepthChartModel. If False, returns raw dict. Default: True

**Returns:**
- `TeamDepthChartModel` (if convert_results=True): Depth chart model with position attributes
- `dict` (if convert_results=False): Raw API response

**Raises:**
- `ValueError`: If team abbreviation is invalid
- `SleeperAPIError`: If the API request fails

**Example:**
```python
# Get 49ers depth chart
depth_chart = nfl_endpoint.get_team_depth_chart('SF')

# Access positions
print(f"Starting QB: {depth_chart.qb[0]}")  # First QB is starter
print(f"Backup QB: {depth_chart.qb[1]}")    # Second QB is backup
print(f"All RBs: {depth_chart.rb}")         # All RBs in depth order

# Get all starters
starters = depth_chart.get_starters()
print(f"QB: {starters['QB']}")
print(f"RB: {starters['RB']}")
print(f"WR1: {starters['WR1']}")

# Get raw response
raw_data = nfl_endpoint.get_team_depth_chart('KC', convert_results=False)
```

**TeamDepthChartModel Attributes:**

Offensive Positions:
- `qb` - Quarterbacks
- `rb` - Running Backs
- `wr1` - Wide Receiver 1
- `wr2` - Wide Receiver 2
- `wr3` - Wide Receiver 3
- `te` - Tight Ends
- `ol` - Offensive Line

Defensive Positions:
- `db` - Defensive Backs
- `dl` - Defensive Line
- `fs` - Free Safety
- `ss` - Strong Safety
- `lb` - Linebackers
- `mlb` - Middle Linebacker
- `lolb` - Left Outside Linebacker
- `rolb` - Right Outside Linebacker
- `lcb` - Left Cornerback
- `rcb` - Right Cornerback
- `lde` - Left Defensive End
- `rde` - Right Defensive End
- `ldt` - Left Defensive Tackle
- `rdt` - Right Defensive Tackle
- `nb` - Nickelback

Special Teams:
- `k` - Kicker
- `p` - Punter
- `ls` - Long Snapper

**Helper Methods:**
```python
# Get starting player for each position
starters = depth_chart.get_starters()
# Returns: {'QB': 'player_id', 'RB': 'player_id', ...}

# Convert to dict
depth_dict = depth_chart.to_dict()
```

---

### get_schedule()

Fetch the NFL schedule for a specific season.

**Signature:**
```python
def get_schedule(
    year: int,
    postseason: bool = False,
    convert_results: bool = True
) -> Union[NFLScheduleModel, List[dict]]
```

**Parameters:**
- `year` (int): NFL season year (2009 or later, not future years)
- `postseason` (bool, optional): If True, fetch playoff schedule. If False, fetch regular season. Default: False
- `convert_results` (bool, optional): If True, returns NFLScheduleModel. If False, returns raw list. Default: True

**Returns:**
- `NFLScheduleModel` (if convert_results=True): Schedule model with helper methods
- `List[dict]` (if convert_results=False): Raw API response

**Raises:**
- `ValueError`: If year is before 2009 or in the future
- `SleeperAPIError`: If the API request fails

**Example:**
```python
# Get 2024 regular season schedule
schedule = nfl_endpoint.get_schedule(2024, postseason=False)

# Access all games
print(f"Total games: {len(schedule.games)}")

# Get games by week
week_1 = schedule.get_games_by_week(1)
for game in week_1:
    print(f"{game.away} @ {game.home} on {game.date}")

# Get games by team
sf_schedule = schedule.get_games_by_team('SF')
print(f"49ers play {len(sf_schedule)} games")

# Get playoff schedule
playoffs = nfl_endpoint.get_schedule(2024, postseason=True)
print(f"Playoff games: {len(playoffs.games)}")

# Get raw response
raw_schedule = nfl_endpoint.get_schedule(2023, convert_results=False)
```

**NFLScheduleModel Attributes:**
- `year` (int): Season year
- `season_type` (str): 'regular' or 'post'
- `games` (List[ScheduleGameModel]): List of all games

**NFLScheduleModel Helper Methods:**
```python
# Get games for specific week
week_games = schedule.get_games_by_week(week=1)

# Get games for specific team
team_games = schedule.get_games_by_team(team='SF')

# Convert to dict
schedule_dict = schedule.to_dict()
```

**ScheduleGameModel Attributes:**
- `game_id` (str): Unique game identifier
- `status` (str): Game status ('scheduled', 'in_progress', 'final')
- `date` (str): Game date in ISO format (e.g., '2023-09-10')
- `home` (str): Home team abbreviation
- `away` (str): Away team abbreviation
- `week` (int): Week number
- `season_type` (str): 'regular' or 'post'

---

### get_regular_season_schedule()

Convenience method to fetch regular season schedule.

**Signature:**
```python
def get_regular_season_schedule(
    year: int,
    convert_results: bool = True
) -> Union[NFLScheduleModel, List[dict]]
```

**Parameters:**
- `year` (int): NFL season year (2009 or later)
- `convert_results` (bool, optional): Return model or raw data. Default: True

**Returns:**
Same as `get_schedule(year, postseason=False, convert_results)`

**Example:**
```python
# Equivalent to get_schedule(2024, postseason=False)
schedule = nfl_endpoint.get_regular_season_schedule(2024)
```

---

### get_postseason_schedule()

Convenience method to fetch postseason schedule.

**Signature:**
```python
def get_postseason_schedule(
    year: int,
    convert_results: bool = True
) -> Union[NFLScheduleModel, List[dict]]
```

**Parameters:**
- `year` (int): NFL season year (2009 or later)
- `convert_results` (bool, optional): Return model or raw data. Default: True

**Returns:**
Same as `get_schedule(year, postseason=True, convert_results)`

**Example:**
```python
# Equivalent to get_schedule(2024, postseason=True)
playoffs = nfl_endpoint.get_postseason_schedule(2024)
```

---

## Complete Examples

### Example 1: Analyzing Team Depth Charts

```python
from sleeper_api import SleeperClient, NFLEndpoint

client = SleeperClient()
nfl = NFLEndpoint(client)

# Get depth charts for multiple teams
teams = ['SF', 'KC', 'BUF', 'PHI']

for team in teams:
    depth_chart = nfl.get_team_depth_chart(team)
    starters = depth_chart.get_starters()

    print(f"\n{team} Starters:")
    print(f"  QB: {starters.get('QB')}")
    print(f"  RB: {starters.get('RB')}")
    print(f"  WR1: {starters.get('WR1')}")
    print(f"  WR2: {starters.get('WR2')}")
    print(f"  TE: {starters.get('TE')}")
```

### Example 2: Finding Team Matchups

```python
from sleeper_api import SleeperClient, NFLEndpoint

client = SleeperClient()
nfl = NFLEndpoint(client)

# Get schedule
schedule = nfl.get_schedule(2024, postseason=False)

# Find when 49ers play Chiefs
sf_games = schedule.get_games_by_team('SF')
kc_games = schedule.get_games_by_team('KC')

# Find common games (SF vs KC)
for sf_game in sf_games:
    for kc_game in kc_games:
        if sf_game.game_id == kc_game.game_id:
            print(f"SF vs KC: Week {sf_game.week} - {sf_game.date}")
            print(f"Location: {sf_game.home} (home team)")
```

### Example 3: Weekly Game Schedule

```python
from sleeper_api import SleeperClient, NFLEndpoint

client = SleeperClient()
nfl = NFLEndpoint(client)

# Get current season schedule
schedule = nfl.get_regular_season_schedule(2024)

# Print schedule for each week
for week in range(1, 19):  # 18 weeks in NFL season
    games = schedule.get_games_by_week(week)
    print(f"\nWeek {week} ({len(games)} games):")

    for game in games:
        print(f"  {game.away} @ {game.home} - {game.date} ({game.status})")
```

### Example 4: Combining with Player Endpoint

```python
from sleeper_api import SleeperClient, NFLEndpoint, PlayerEndpoint

client = SleeperClient()
nfl = NFLEndpoint(client)
player = PlayerEndpoint(client)

# Get player database
players_dict = {p.player_id: p for p in player.get_all_players()}

# Get 49ers depth chart
depth_chart = nfl.get_team_depth_chart('SF')

# Print QB depth chart with names
print("49ers QB Depth Chart:")
for i, player_id in enumerate(depth_chart.qb, 1):
    if player_id in players_dict:
        player_name = f"{players_dict[player_id].first_name} {players_dict[player_id].last_name}"
        print(f"  {i}. {player_name} (ID: {player_id})")
```

### Example 5: Historical Schedule Analysis

```python
from sleeper_api import SleeperClient, NFLEndpoint
from collections import Counter

client = SleeperClient()
nfl = NFLEndpoint(client)

# Analyze last 5 seasons
seasons = [2019, 2020, 2021, 2022, 2023]
team_stats = Counter()

for year in seasons:
    schedule = nfl.get_regular_season_schedule(year)

    # Count games per team
    for game in schedule.games:
        team_stats[game.home] += 1
        team_stats[game.away] += 1

# Print results
print("Games per team over 5 seasons:")
for team, count in team_stats.most_common():
    print(f"  {team}: {count} games")
```

## Error Handling

Always handle potential errors when working with undocumented endpoints:

```python
from sleeper_api import SleeperClient, NFLEndpoint
from sleeper_api.exceptions import SleeperAPIError

client = SleeperClient()
nfl = NFLEndpoint(client)

try:
    depth_chart = nfl.get_team_depth_chart('SF')
    print(f"QB: {depth_chart.qb}")
except ValueError as e:
    print(f"Invalid input: {e}")
except SleeperAPIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Handle schedule year validation
try:
    schedule = nfl.get_schedule(2008)  # Before 2009
except ValueError as e:
    print(f"Year validation failed: {e}")

try:
    schedule = nfl.get_schedule(2030)  # Future year
except ValueError as e:
    print(f"Cannot fetch future schedules: {e}")
```

## Best Practices

1. **Cache Depth Charts**: Depth charts can change weekly, consider caching for short periods
2. **Cache Schedules**: Schedules are static once published, safe to cache long-term
3. **Error Handling**: Always wrap API calls in try-except blocks
4. **Team Abbreviations**: Use standard NFL abbreviations (SF, KC, NE, etc.)
5. **Year Validation**: Check year range (2009-present) before calling schedule endpoint
6. **Rate Limiting**: Be mindful of API rate limits when fetching multiple teams/years

## Limitations

- **Undocumented Endpoints**: These endpoints are not officially documented and may change
- **Schedule History**: Only available from 2009 onwards
- **Future Schedules**: Cannot fetch schedules for future seasons
- **Real-time Updates**: Depth charts may not update immediately after roster changes
- **No Injury Data**: Depth charts don't include injury status
- **No Player Stats**: Only returns player IDs, not stats or details

## Related Endpoints

- **PlayerEndpoint**: Get player details by ID from depth charts
- **LeagueEndpoint**: Get fantasy league matchups and rosters
- **ProjectionsEndpoint**: Get player projections for fantasy analysis

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/smallery/sleeper_fantasy_api/issues
- **Email**: sleeperfantasyapi@gmail.com

---

*Last Updated: 2026-01-15 (v0.3.0)*
