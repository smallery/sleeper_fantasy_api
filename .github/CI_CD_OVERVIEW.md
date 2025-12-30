# CI/CD Overview

This document provides an overview of the continuous integration and continuous deployment (CI/CD) setup for the sleeper_fantasy_api project.

## Workflows

### 1. Tests Workflow (`tests.yml`)

**Triggers**: Push to main/master, Pull Requests to main/master

**Jobs**:

- **test**: Runs the full test suite
  - Matrix: Python 3.10, 3.11, 3.12 on Ubuntu
  - Installs dependencies from requirements.txt
  - Runs pytest with coverage reporting
  - Uploads coverage to Codecov (Python 3.11 only)

- **lint**: Code quality checks
  - Runs flake8 for syntax errors and style violations
  - Enforces code quality standards

- **import-check**: Module import validation
  - Verifies all modules can be imported successfully
  - Tests: Client, Endpoints, Models, Cache

**Purpose**: Ensure code quality and functionality on main branches

---

### 2. PR Tests Workflow (`pr-tests.yml`)

**Triggers**: Pull Request events (opened, synchronize, reopened)

**Jobs**:

- **test-all**: Comprehensive test suite
  - Runs all tests in parallel using pytest-xdist
  - Generates HTML coverage reports
  - Breaks down tests by module type
  - Uploads test results as artifacts

- **test-new-features**: Focused testing for new features
  - Projections Endpoint tests
  - Persistent Cache tests
  - NFL State Model tests
  - Team Variance Model tests

- **test-compatibility**: Cross-platform testing
  - Matrix: Ubuntu, macOS, Windows
  - Matrix: Python 3.10, 3.11
  - Runs smoke tests on all platforms

**Purpose**: Thorough validation of pull requests before merging

---

### 3. Code Quality Workflow (`code-quality.yml`)

**Triggers**: Push to main/master, Pull Requests to main/master

**Jobs**:

- **quality**: Code formatting and type checking
  - black: Code formatting validation
  - isort: Import sorting validation
  - flake8: Linting
  - mypy: Type checking (informational)

- **security**: Security scanning
  - safety: Dependency vulnerability checking
  - bandit: Security issue detection in code

**Purpose**: Maintain code quality and security standards

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
