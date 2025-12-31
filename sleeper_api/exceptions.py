class SleeperAPIError(Exception):
    """Base exception for Sleeper API errors."""

    def __init__(self, message: str, status_code: int = None):
        """
        Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if applicable.
        """
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class UserNotFoundError(SleeperAPIError):
    """Raised when a username is not found (404)."""

    def __init__(self, username: str):
        """
        Initialize the exception.

        Args:
            username: The username that was not found.
        """
        super().__init__(
            message=f"User '{username}' not found",
            status_code=404,
        )
        self.username = username


class RateLimitError(SleeperAPIError):
    """Raised when rate limited (429) after exhausting retries."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """
        Initialize the exception.

        Args:
            message: Error message.
        """
        super().__init__(message=message, status_code=429)


class LeagueNotFoundError(SleeperAPIError):
    """Raised when a league is not found."""

    def __init__(self, league_id: str):
        """
        Initialize the exception.

        Args:
            league_id: The league ID that was not found.
        """
        super().__init__(
            message=f"League '{league_id}' not found",
            status_code=404,
        )
        self.league_id = league_id
