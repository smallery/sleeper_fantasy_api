# Test Suite Documentation

This directory contains the comprehensive test suite for sleeper_fantasy_api.

## Test Organization

Tests are organized by module type for efficient execution and maintenance:

### Model Tests (`test_model_*.py`)
Tests for data models representing Sleeper API objects:
- `test_model_brackets.py` - Playoff brackets
- `test_model_draft.py` - Draft information
- `test_model_league.py` - League settings and configuration
- `test_model_matchups.py` - Weekly matchups
- `test_model_nfl_state.py` - **NEW**: NFL season/week state
- `test_model_picks.py` - Draft picks
- `test_model_player.py` - Player information
- `test_model_roster.py` - Team rosters
- `test_model_traded_picks.py` - Traded draft picks
- `test_model_transactions.py` - League transactions
- `test_model_user.py` - User information
- `test_model_variance.py` - **NEW**: Team scoring variance

### Endpoint Tests (`test_endpoint_*.py`)
Tests for API endpoint wrappers:
- `test_endpoint_draft.py` - Draft endpoint
- `test_endpoint_league.py` - League endpoint
- `test_endpoint_player.py` - Player endpoint
- `test_endpoint_user.py` - User endpoint

### New Feature Tests
- `test_projections_endpoint.py` - **NEW**: Player projections and analytics
- `test_persistent_cache.py` - **NEW**: File-based caching system

### Core Tests
- `test_client.py` - SleeperClient HTTP client with retry logic
- `test_integration.py` - End-to-end integration tests
- `test_performance.py` - Performance benchmarks

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# Models only
pytest tests/test_model_*.py -v

# Endpoints only
pytest tests/test_endpoint_*.py -v

# New features only
pytest tests/test_projections_endpoint.py tests/test_persistent_cache.py -v

# Core only
pytest tests/test_client.py tests/test_integration.py -v
```

### Performance
- **96 tests** in ~1.6 seconds
- Parallel execution: `pytest -n auto`
- With coverage: `pytest --cov=sleeper_api`

For full documentation, see [CONTRIBUTING.md](../CONTRIBUTING.md)
