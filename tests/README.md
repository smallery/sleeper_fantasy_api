Unit and Integration tests for API Wrapper
Each test file corresponds to a module in the resources directory

*Plan* use pytest to write and organize tests

Running Tests:
Run tests by executing `pytest tests/` in the directory ./sleeper_fantasy_api/
- activate virtual environment first
_if needed you may have to set the python path specifically for this to work_ : `PYTHONPATH=$(pwd) pytest tests/` instead 

Test Coverage:
- install pytest-cov
- run `pytest --cov=sleeper_api tests/

If needed, you may have to specify