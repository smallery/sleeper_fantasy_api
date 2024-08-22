from typing import List, Optional
from datetime import datetime
from .league import LeagueModel

class UserModel:
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
        return f"<UserModel(username={self.username}, user_id={self.user_id}, display_name={self.display_name}, nfl_leagues={len(self.nfl_leagues)})>"

    def set_nfl_leagues(self, leagues: List[LeagueModel]):
        """Set the NFL leagues for the user."""
        self.nfl_leagues = leagues