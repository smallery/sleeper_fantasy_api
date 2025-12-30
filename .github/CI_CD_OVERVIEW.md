# CI/CD Overview

This document provides an overview of the continuous integration and continuous deployment (CI/CD) setup for the sleeper_fantasy_api project.

## Workflows

### CI Workflow (`ci.yml`)

**Single, efficient workflow that runs on all PRs and pushes to main/master**

**Triggers**: Push to main/master, Pull Requests

**Jobs** (runs in parallel):

1. **test**: Runs the full test suite
   - Matrix: Python 3.10, 3.11, 3.12 on Ubuntu
   - Installs package in development mode (`pip install -e .`)
   - Runs pytest with coverage reporting
   - Uploads coverage to Codecov (Python 3.11 only, PR only)
   - **Fast**: Uses pip cache for faster dependency installation

2. **lint**: Code quality checks
   - Runs flake8 for syntax errors (blocking)
   - Runs flake8 for style violations (non-blocking)
   - **Fast**: Uses pip cache

3. **imports**: Module import validation
   - Installs package in development mode
   - Verifies all new modules can be imported successfully
   - Tests: Client, ProjectionsEndpoint, PersistentCache, NFLStateModel, TeamVarianceModel

**Total Checks**: 5 (3 test jobs + 1 lint + 1 import)

**Purpose**: Fast, efficient CI/CD with minimal redundancy

---

## Previous Setup (Removed for Efficiency)

We previously had 11 separate checks across 5 workflows:
- ❌ tests.yml (5 jobs)
- ❌ pr-tests.yml (3 jobs)
- ❌ code-quality.yml (2 jobs)
- ❌ pytest.yml (1 job)
- ❌ pylint.yml (1 job)

**Problem**: Too many redundant jobs, slow feedback, wasted CI minutes

**Solution**: Single `ci.yml` workflow with 3 parallel jobs = **5 total checks**

---

## Key Improvements

### 1. Package Installation
All workflows now properly install the package:
```bash
pip install -e .  # Installs sleeper_api in development mode
```
This fixes `ModuleNotFoundError: No module named 'sleeper_api'`

### 2. Pip Caching
Uses GitHub Actions pip cache for faster runs:
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'  # Caches dependencies
```

### 3. Parallel Execution
All 3 jobs run in parallel for fastest feedback.

### 4. Fail-Fast Disabled
Matrix continues testing all Python versions even if one fails.

---

## Test Configuration

### pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
minversion = "6.0"
addopts = [
    "-ra",              # Show all test summary info
    "-q",               # Quiet output
    "--strict-markers", # Strict marker usage
    "--cov=sleeper_api", # Coverage for sleeper_api
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Coverage Configuration (`.coveragerc`)

- **Source**: sleeper_api
- **Omit**: tests, __pycache__, site-packages
- **Reports**: HTML (htmlcov/), XML (coverage.xml), Terminal

---

## Running Tests Locally

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=sleeper_api --cov-report=html
```

### Run Tests in Parallel

```bash
pytest -n auto
```

### Run Specific Test Files

```bash
# New features
pytest tests/test_projections_endpoint.py -v
pytest tests/test_persistent_cache.py -v
pytest tests/test_model_nfl_state.py -v
pytest tests/test_model_variance.py -v

# Existing features
pytest tests/test_client.py -v
pytest tests/test_endpoint_*.py -v
pytest tests/test_model_*.py -v
```

### Run Tests by Marker

```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not slow"    # Skip slow tests
```

---

## Code Quality Checks

### Format Code

```bash
black sleeper_api tests examples --line-length 100
```

### Sort Imports

```bash
isort sleeper_api tests examples --profile black
```

### Lint Code

```bash
flake8 sleeper_api --max-line-length=127
```

### Type Check

```bash
mypy sleeper_api --ignore-missing-imports
```

---

## Coverage Goals

- **Target**: 80%+ code coverage
- **Current**: View on [Codecov](https://codecov.io/gh/smallery/sleeper_fantasy_api)
- **Reports**:
  - Terminal output during test runs
  - HTML report in `htmlcov/`
  - XML report for Codecov

---

## PR Checklist

Before submitting a PR, ensure:

- ✅ All tests pass locally
- ✅ Code is formatted with black
- ✅ Imports are sorted with isort
- ✅ No flake8 violations
- ✅ Coverage is maintained or improved
- ✅ New features have tests
- ✅ Documentation is updated

---

## CI/CD Status

Check the status of CI/CD workflows:

- **Tests**: ![Tests](https://github.com/smallery/sleeper_fantasy_api/workflows/Tests/badge.svg)
- **Code Quality**: ![Code Quality](https://github.com/smallery/sleeper_fantasy_api/workflows/Code%20Quality/badge.svg)
- **Coverage**: ![codecov](https://codecov.io/gh/smallery/sleeper_fantasy_api/branch/main/graph/badge.svg)

---

## Troubleshooting

### Tests Fail Locally but Pass in CI

- Ensure you have the latest dependencies: `pip install -r requirements.txt`
- Check Python version matches CI (3.10, 3.11, or 3.12)
- Clear pytest cache: `pytest --cache-clear`

### Coverage Too Low

- Add tests for new features
- Test edge cases and error conditions
- Use `pytest --cov-report=html` to see uncovered lines
- Focus on critical paths first

### Import Errors in CI

- Verify all new modules are in `__init__.py`
- Check for circular imports
- Ensure dependencies are in requirements.txt

---

## Future Enhancements

Potential improvements:

- [ ] Integration tests with live Sleeper API (using VCR.py)
- [ ] Performance benchmarking
- [ ] Automated release workflow
- [ ] Documentation generation (Sphinx)
- [ ] Pre-commit hooks
- [ ] Automated dependency updates (Dependabot)

---

For more information, see [CONTRIBUTING.md](../CONTRIBUTING.md)
