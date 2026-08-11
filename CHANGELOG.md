# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-10

### Changed
- **Dependencies are no longer exact pins** (the headline fix of this release).
  `0.3.0` shipped `platformdirs==3.8.1`, `requests==2.31.0`, and `pytest==8.2.2`
  as `==` pins. Because pip applies a library's constraints to the whole
  resolution, every consuming application inherited them and could not move off
  them. Real consequences reported downstream:
  - `requests` could not be upgraded past 2.31.0, holding applications on a
    release with 3 known CVEs (including CVE-2024-35195, fixed in 2.32.0) with
    no newer version of this package to bump to.
  - `pip-audit` could not be installed at all in the same environment, since it
    requires `platformdirs>=4.2.0`.
  - Applications were held to `pytest` 8.2.2 and to releases predating Python 3.13.

  Now declared as `platformdirs>=4.2.0,<5` and `requests>=2.32.0,<3`.

- **`pytest` is no longer a runtime dependency.** It was listed under
  `[project.dependencies]`, so installing this package installed a test
  framework and constrained the consumer's own test suite. Nothing in
  `sleeper_api` imports it. It now lives in the `dev` extra:
  `pip install "sleeper_fantasy_api[dev]"`.

- **`Retry-After` is now honored** on retryable responses, in both RFC 9110
  forms (delta-seconds and HTTP-date). The server's instruction takes precedence
  over the local exponential backoff — retrying sooner than asked just burns
  attempts against a door that is still closed. urllib3's `Retry` honored this
  for the codes in `status_forcelist`, so keeping it preserves 5xx behavior
  through the retry consolidation below; **429 was never in that forcelist**, so
  rate limits gain handling they never had. A `Retry-After` longer than
  `MAX_RETRY_AFTER_SECONDS` (60s) raises immediately rather than blocking the
  caller — this library runs inside web request handlers, where a ten-minute
  sleep is worse than a fast failure.

- **Single retry layer in `SleeperClient`.** The session mounted an
  `HTTPAdapter` carrying a urllib3 `Retry(total=3)` *and* `_request` ran its own
  retry loop, so the two multiplied: one outage could cost up to
  `(max_retries + 1) x 4` requests with both backoff schedules stacked. Retry is
  now handled solely by `_request`, which covers rate limits (429), transient
  server errors (500/502/503/504), and transport exceptions with the documented
  exponential backoff. The adapter is mounted with `max_retries=0`.

- Connection pool widened (`pool_maxsize=20`) so concurrent fetches are not
  serialized on connection checkout.

### Added
- **`max_workers` on `get_season_projections()` and
  `get_player_season_projections()`.** Fans the requested weeks out over a
  thread pool (capped at 8); results and key order are identical to the
  sequential path. Defaults to `1`, so existing behavior is unchanged unless
  opted into.

  ```python
  projections = endpoint.get_season_projections(
      2025, weeks=list(range(10, 19)), max_workers=8
  )
  ```

  Measured against the live API (2025 season, 18 weeks, warm connection pool):
  **~0.8s sequential vs ~0.35s with 8 workers**. The network portion alone
  parallelizes ~3.4x; the remainder is GIL-bound cache serialization. Note that
  a week of projections is ~0.55 MB, not the multiple megabytes sometimes
  assumed — 18 weeks is ~9.4 MB total. The benefit also depends on connection
  reuse: each worker needs its own pooled connection and a TLS handshake costs
  ~0.3s against ~0.03s for a warm request, so over a cold pool with only a few
  weeks the fan-out can be a wash or slightly slower. See the method docstring.

- `examples/example_projections_usage.py` now demonstrates concurrent
  multi-week fetching and per-player week-over-week tracking.
- Python 3.13 added to the CI matrix, and explicit 3.10-3.13 classifiers so
  supported versions are visible on PyPI. `requires-python` is unchanged (`>=3.10`).
- `pip-audit` added to `requirements-dev.txt` — it could not be installed
  alongside this package before the `platformdirs` pin was lifted.

### Performance
- **Cache writes are ~5x faster.** `PersistentCache.set()` used
  `json.dump(value, file)`, which falls back to Python's incremental encoder;
  it now serializes with `json.dumps()` (the C encoder) and writes the result.
  On a ~0.55 MB projections payload that is 44ms → 8.5ms. This is the dominant
  cost of a bulk fetch once the network is parallelized, and it speeds up the
  ordinary sequential path just as much. Serializing before opening the file
  also means a value that fails to encode no longer leaves a half-written cache
  file behind.

### Fixed
- **`PersistentCache` metadata race.** `set()`, `invalidate()`, `clear()`, and
  `cleanup_expired()` perform a read-modify-write on one shared metadata file
  with no synchronization. Under concurrent access, interleaved writes corrupt
  the file or drop entries — and because `get()` treats a cache file with no
  metadata entry as having no expiry, a dropped entry means that key is served
  stale forever. Now guarded by a re-entrant lock. This was latent before, and
  reachable as soon as `max_workers > 1`.
- Replaced the deprecated `requests.packages.urllib3` import path (removed
  along with the adapter-level `Retry`).
- **`examples/example_projections_usage.py` could not run at all.** It called
  `UserEndpoint.get_leagues()`, which has never existed (the method is
  `fetch_nfl_leagues()`), and then treated the returned `LeagueModel` objects as
  dicts. It also fetched projections for the current week, which returns nothing
  during preseason, and ended on an emoji that raises `UnicodeEncodeError` on a
  cp1252 Windows console. Now verified end-to-end against the live API.

## [0.3.0] - 2026-01-15

### Added
- **NFL Endpoint** - New endpoint for undocumented NFL-specific Sleeper API features
  - `get_team_depth_chart(team)` - Fetch depth chart for any NFL team
  - `get_schedule(year, postseason)` - Get NFL schedule (regular season or playoffs)
  - `get_regular_season_schedule(year)` - Convenience method for regular season
  - `get_postseason_schedule(year)` - Convenience method for playoffs
  - Supports schedule data from 2009 to present
- **League Endpoint Enhancement** - Convenience method for common use case
  - `get_complete_league_data(league_id)` - Fetch league, rosters, and users in one call
  - Returns dict with league, rosters, users, and roster_to_user mapping
  - Simplifies common pattern of fetching all league data at once
- **New Models**:
  - `TeamDepthChartModel` - NFL team depth charts with all position groups
  - `NFLScheduleModel` - Complete season schedule with helper methods
  - `ScheduleGameModel` - Individual game data (teams, date, status, week)
- **Enhanced Documentation**:
  - Added comprehensive docstrings to `UserModel`, `LeagueModel`, `RosterModel`, `MatchupModel`
  - All model classes now document attributes, types, and usage examples
  - Better IDE autocomplete and type hinting support
  - Created `docs/NFL_ENDPOINT.md` with complete API reference and examples
  - Created `AGENT.md` for transparency about AI-assisted development
  - Created `CLAUDE.md` with technical details of development process

### Fixed
- **Public API Export** - `ProjectionsEndpoint` now properly exported from main package
  - Can now use `from sleeper_api import ProjectionsEndpoint` (was previously requiring internal import path)
  - Consistent with other endpoint exports

### Notes
**Implemented Enhancement Requests**:
- ✅ Export ProjectionsEndpoint in public API
- ✅ Add comprehensive model documentation
- ✅ Complete league data convenience method - Reconsidered and implemented per user request

**Enhancement Requests Evaluated and Declined**:
The following requests were evaluated but declined as they fall outside the scope of an API wrapper:
- ❌ Optimal lineup calculation - business logic, not API functionality
- ❌ Batch matchup fetching - minimal value over simple loop
- ❌ Team variance calculation - statistical analysis, not API functionality

These features belong in separate analytics/helper packages built on top of this API wrapper.

**Enhancement Requests Deferred**:
- ⏸️ Type stubs (.pyi files) - valuable but requires dedicated effort
- ⏸️ Async support - significant architectural change, warrants separate major version

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

[0.3.0]: https://github.com/smallery/sleeper_fantasy_api/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/smallery/sleeper_fantasy_api/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/smallery/sleeper_fantasy_api/releases/tag/v0.1.0
