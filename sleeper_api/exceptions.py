class SleeperAPIError(Exception):
    """Base class for exceptions in this module."""
    pass

class UserNotFoundError(SleeperAPIError):
    """Raised when a user is not found."""
    pass
