# Contributing to sleeper_fantasy_api

Thank you for considering contributing to sleeper_fantasy_api! This document outlines the process and guidelines for contributing.

## Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/sleeper_fantasy_api.git
   cd sleeper_fantasy_api
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest-cov pytest-xdist black isort flake8
   ```

3. **Create a new branch**:
   ```bash
   git checkout -b your-username/feature-name
   ```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=sleeper_api --cov-report=html
```

### Run tests in parallel
```bash
pytest -n auto
```

### Run specific test files
```bash
pytest tests/test_projections_endpoint.py -v
```

### Run tests by marker
```bash
pytest -m unit  # Run only unit tests
pytest -m "not slow"  # Skip slow tests
```

## Code Quality

### Format code with black
```bash
black sleeper_api tests examples --line-length 100
```

### Sort imports with isort
```bash
isort sleeper_api tests examples --profile black
```

### Lint with flake8
```bash
flake8 sleeper_api --max-line-length=127
```

## Continuous Integration

All pull requests automatically run:

1. **Tests** - Multiple Python versions (3.10, 3.11, 3.12) on Ubuntu, macOS, and Windows
2. **Code Quality** - Formatting, linting, type checking
3. **Security** - Dependency vulnerability scanning
4. **Import Checks** - Verify all modules can be imported
5. **Coverage** - Test coverage reporting

### CI/CD Workflows

- **`tests.yml`** - Main test suite on push and PR
- **`pr-tests.yml`** - Comprehensive PR testing including new features
- **`code-quality.yml`** - Code quality and security checks

## Pull Request Process

1. **Write tests** for any new features or bug fixes
   - Add tests in the appropriate `tests/test_*.py` file
   - Ensure tests cover edge cases and error conditions
   - Aim for >80% code coverage

2. **Update documentation**
   - Update docstrings for new/modified functions
   - Update README.md if adding new features
   - Add examples if appropriate

3. **Run tests locally**
   ```bash
   pytest --cov=sleeper_api
   ```

4. **Format and lint code**
   ```bash
   black sleeper_api tests examples
   isort sleeper_api tests examples --profile black
   flake8 sleeper_api
   ```

5. **Commit with descriptive messages**
   ```bash
   git add .
   git commit -m "feat: Add new feature description"
   ```

6. **Push to your fork**
   ```bash
   git push origin your-username/feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear title and description
   - Reference any related issues
   - Wait for CI checks to pass
   - Address any review feedback

## Commit Message Guidelines

Follow conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `style:` - Formatting changes
- `chore:` - Maintenance tasks

Example:
```
feat: Add player projections endpoint

- Implement get_projections() method
- Add persistent caching for projections
- Support PPR/Half-PPR/Standard scoring
```

## Adding New Features

### 1. New Endpoints

When adding a new endpoint:

1. Create endpoint class in `sleeper_api/endpoints/`
2. Add corresponding model in `sleeper_api/models/` if needed
3. Update `__init__.py` files to export new classes
4. Write comprehensive tests in `tests/`
5. Add usage examples in `examples/`
6. Update README.md with new endpoint documentation

### 2. New Models

When adding a new model:

1. Create model class in `sleeper_api/models/`
2. Implement `from_dict()` and `to_dict()` methods
3. Add type hints and docstrings
4. Write model tests in `tests/test_model_*.py`
5. Update `sleeper_api/models/__init__.py`

### 3. New Utilities

When adding utilities:

1. Add to appropriate module or create new utility module
2. Write comprehensive tests
3. Document usage in docstrings

## Testing Guidelines

### Test Structure

```python
"""Tests for the FeatureName class."""
import pytest
from sleeper_api.feature import Feature


class TestFeature:
    """Test cases for Feature."""

    @pytest.fixture
    def feature(self):
        """Create a Feature instance for testing."""
        return Feature()

    def test_basic_functionality(self, feature):
        """Test basic feature functionality."""
        result = feature.do_something()
        assert result is not None

    def test_error_handling(self, feature):
        """Test error handling."""
        with pytest.raises(ValueError):
            feature.do_invalid_thing()
```

### Test Coverage

- Aim for >80% code coverage
- Test both success and failure cases
- Test edge cases and boundary conditions
- Use mocks for external API calls
- Test with various Python versions

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write clear, descriptive docstrings
- Keep functions focused and single-purpose
- Use meaningful variable names
- Maximum line length: 127 characters (flake8) or 100 (black)

## Questions?

If you have questions, please:

1. Check existing issues and pull requests
2. Open a new issue for discussion
3. Contact the maintainer: [Sam Mallery](mailto:sleeperfantasyapi@gmail.com)

Thank you for contributing! 🎉
