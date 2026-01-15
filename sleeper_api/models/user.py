from typing import List, Optional
from datetime import datetime
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
    def __init__(self, username: str, user_id: str, display_name: str, avatar: str):
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

        if self.avatar:
            avatar_full_size_url = f'https://sleepercdn.com/avatars/{self.avatar}'
            avatar_thumbnail_url = f'https://sleepercdn.com/avatars/thumbs/{self.avatar}'

    @classmethod
    def from_json(cls, data: dict):
        """
        Create a UserModel instance from a JSON dictionary.

        :param data: A dictionary containing user data.
        :return: An instance of UserModel.
        """
        return cls(
            username=data.get("username"),
            user_id=data.get("user_id"),
            display_name=data.get("display_name"),
            avatar=data.get("avatar")
        )

    def __repr__(self):
        return f"<UserModel(username={self.username}, user_id={self.user_id}, display_name={self.display_name})>"
    