"""
This module provides access to key endpoints of the Sleeper API.

It imports and exposes the following endpoint classes:
- `UserEndpoint`: For interacting with user-related API endpoints.
- `LeagueEndpoint`: For managing league-related API endpoints.
- `DraftEndpoint`: For handling draft-related API endpoints.
- `PlayerEndpoint`: For accessing player-related API endpoints.

Usage:
------
To use the provided endpoint classes, import them from this module:

    >>> from your_module import UserEndpoint, LeagueEndpoint, DraftEndpoint, PlayerEndpoint

    # Example usage
    >>> user_endpoint = UserEndpoint(client)
    >>> league_endpoint = LeagueEndpoint(client)
    >>> draft_endpoint = DraftEndpoint(client)
    >>> player_endpoint = PlayerEndpoint(client)

This module makes it convenient to work with different parts of the Sleeper API
by organizing related endpoints into separate classes.

Note:
-----
The `__all__` list controls what is imported when `from your_module import *` is used. It includes:
- `UserEndpoint`
- `LeagueEndpoint`
- `DraftEndpoint`
- `PlayerEndpoint`
"""


from .draft_endpoint import DraftEndpoint
from .league_endpoint import LeagueEndpoint
from .nfl_endpoint import NFLEndpoint
from .player_endpoint import PlayerEndpoint
from .projections_endpoint import ProjectionsEndpoint
from .user_endpoint import UserEndpoint

__all__ = [
    "UserEndpoint",
    "LeagueEndpoint",
    "DraftEndpoint",
    "PlayerEndpoint",
    "ProjectionsEndpoint",
    "NFLEndpoint",
]
