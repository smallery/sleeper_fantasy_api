"""
Tests for the public package surface (sleeper_api/__init__.py).

Only SleeperAPIError and UserNotFoundError used to be exported, so
consumers had to reach into sleeper_api.exceptions directly for
RateLimitError and LeagueNotFoundError -- exactly what the downstream
consumer referenced in issue #17 was doing. All four belong in __all__
since anything a caller is expected to catch belongs in the public API.
"""
import unittest

import sleeper_api
from sleeper_api import (
    LeagueNotFoundError,
    RateLimitError,
    SleeperAPIError,
    UserNotFoundError,
)


class TestPackageExceptionExports(unittest.TestCase):

    def test_all_four_exception_types_are_importable_from_the_package_root(self):
        # The import above is the real assertion -- it fails at collection
        # time if any of these aren't exported. This just makes the intent
        # explicit and gives a readable failure if one is ever removed.
        for exc_type in (SleeperAPIError, UserNotFoundError, LeagueNotFoundError, RateLimitError):
            self.assertTrue(issubclass(exc_type, Exception))

    def test_all_four_exception_types_are_listed_in_dunder_all(self):
        for name in ("SleeperAPIError", "UserNotFoundError", "LeagueNotFoundError", "RateLimitError"):
            with self.subTest(name=name):
                self.assertIn(name, sleeper_api.__all__)

    def test_not_found_errors_subclass_the_base_error(self):
        # So a caller catching only SleeperAPIError still catches these.
        self.assertTrue(issubclass(UserNotFoundError, SleeperAPIError))
        self.assertTrue(issubclass(LeagueNotFoundError, SleeperAPIError))
        self.assertTrue(issubclass(RateLimitError, SleeperAPIError))


if __name__ == '__main__':
    unittest.main()
