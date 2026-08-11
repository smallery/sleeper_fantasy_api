from typing import List, Optional

from ..exceptions import SleeperAPIError
from .league import LeagueModel


class UserModel:
    """
    Represents a Sleeper user.

    Attributes:
        username: User's unique username (str)
        user_id: Unique user identifier (str)
        display_name: User's display name (str)
        avatar: Avatar image ID (str) - can be used to construct avatar URLs
        nfl_leagues: List of LeagueModel instances for user's NFL leagues (List[LeagueModel])

    Avatar URLs can be constructed as:
        - Full size: https://sleepercdn.com/avatars/{avatar}
        - Thumbnail: https://sleepercdn.com/avatars/thumbs/{avatar}

    Example:
        >>> user = UserModel.from_json(user_data)
        >>> print(f"User: {user.username} ({user.display_name})")
        >>> avatar_url = f"https://sleepercdn.com/avatars/{user.avatar}"
    """
    def __init__(
        self,
        # No `= None` defaults: all four are required arguments and
        # UserModel() must keep raising TypeError for missing arguments,
        # same as before mypy was added. Optional[str] (without a default)
        # describes the *type* -- from_json() supplies these via
        # data.get(...), which mypy types as Optional since the Sleeper
        # payload has no schema guarantee -- it does not make them omittable.
        #
        # user_id is the exception: from_json() rejects a payload without one
        # (see below), so publishing it as Optional would force every caller
        # into a None check for a state that cannot reach them -- and
        # user.user_id is the value they feed straight back into
        # fetch_nfl_leagues(user_id: str).
        username: Optional[str],
        user_id: str,
        display_name: Optional[str],
        avatar: Optional[str],
    ):
        """
        Initialize the UserModel with the provided user data.

        :param username: The username of the user.
        :param user_id: The ID of the user.
        :param display_name: The display name of the user.
        :param avatar: The avatar URL or ID of the user.
        """
        self.username = username
        self.user_id = user_id
        self.display_name = display_name
        self.avatar = avatar
        self.nfl_leagues: List[LeagueModel] = []

    @classmethod
    def from_json(cls, data: dict) -> "UserModel":
        """
        Create a UserModel instance from a JSON dictionary.

        :param data: A dictionary containing user data.
        :return: An instance of UserModel.
        """
        # Sleeper always returns a user_id for a user that exists, and
        # callers pass it straight into APIs typed `user_id: str`. Validate
        # here rather than publishing Optional -- same treatment LeagueModel
        # and DraftModel give their required fields.
        user_id = data.get("user_id")
        if user_id is None:
            raise SleeperAPIError("User payload has no user_id")

        return cls(
            username=data.get("username"),
            user_id=user_id,
            display_name=data.get("display_name"),
            avatar=data.get("avatar"),
        )

    def __repr__(self) -> str:
        return f"<UserModel(username={self.username}, user_id={self.user_id}, display_name={self.display_name})>"
