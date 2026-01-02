# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-02

### Added
- **Player Projections Endpoint** - Access weekly player projections from undocumented Sleeper API
  - `get_projections(season, week)` - Fetch all player projections for a week
  - `get_player_projection(player_id, season, week)` - Fetch single player projection
  - `get_season_projections(season, weeks)` - Bulk fetch across multiple weeks
  - `get_player_season_projections(player_id, season, weeks)` - Track player across season
  - `get_scoring_type(league_id)` - Auto-detect PPR/Half-PPR/Standard scoring
  - `calculate_team_projection(starters, projections, scoring_type)` - Calculate team totals
- **Persistent File Cache** - 24-hour caching for projections to minimize API calls
- **NFL State Model** (`NFLStateModel`) - Get current NFL season, week, and game state via `get_nfl_state()`
- Enhanced exception handling with `RateLimitError` and `LeagueNotFoundError`
- Exponential backoff retry logic for rate limits and network errors in client

### Changed
- Simplified CI/CD from 5 redundant workflows to 1 efficient workflow (4 checks total)
- Removed Codecov integration (no external dependencies)
- Consolidated documentation into README only (removed CONTRIBUTING.md, CI_CD_OVERVIEW.md)
- Simplified testing configuration (removed coverage tracking, test markers)

### Fixed
- Client now returns `None` for 404 responses instead of raising exception
- Improved URL construction and error handling

**Note**: No breaking changes! All existing 0.1.0 code continues to work.

## [0.1.0] - 2024-XX-XX

Initial public release

### Added
- Core API wrapper for Sleeper Fantasy Football API
- User, League, Player, Draft endpoints
- Model classes for all Sleeper API objects
- Comprehensive test coverage
- CI/CD with GitHub Actions

[0.2.0]: https://github.com/smallery/sleeper_fantasy_api/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/smallery/sleeper_fantasy_api/releases/tag/v0.1.0
