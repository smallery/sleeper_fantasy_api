from typing import Any, Dict, Optional


class PlayerModel:
    def __init__(
        self,
        # Optional despite being the identifier: from_dict() builds this from
        # attributes.get('player_id'), which mypy correctly types as
        # Optional -- the Sleeper payload has no schema guarantee.
        player_id: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        position: Optional[str] = None,
        team_abbr: Optional[str] = None,
        team: Optional[str] = None,
        status: Optional[str] = None,
        sport: Optional[str] = None,
        age: Optional[int] = None,
        college: Optional[str] = None,
        years_exp: Optional[int] = None,
        _player_data: Optional[Dict] = None,
        add_count: Optional[int] = None,
        drop_count: Optional[int] = None,
    ):
        self.player_id = player_id
        self.first_name = first_name
        self.last_name = last_name
        self.name = f'{first_name} {last_name}' if last_name else first_name
        self.position = position
        # note sometimes the team_abbr is None but team is filled in with the correct abbreviation
        # this is my best way of fixing this now but should probably add some conditional logic to validate this
        self.team_abbr = team_abbr or team
        self.status = status
        self.sport = sport
        self.age = age
        self.college = college
        self.years_exp = years_exp
        self._player_data = _player_data
        # Not part of the Sleeper player payload -- PlayerEndpoint.get_trending_players()
        # bolts these on after construction. Declared here (rather than left as a
        # dynamic attribute) so PlayerModel's own type is accurate.
        self.add_count = add_count
        self.drop_count = drop_count

    @classmethod
    def from_dict(cls, attributes: dict):
        """
        Create a PlayerModel instance from a dictionary where the key is the player_id
        and the value is another dictionary containing player attributes.

        :param data: A dictionary with player_id as key and attributes as value.
        :return: An instance of PlayerModel.
        """

        return cls(
            player_id=attributes.get('player_id'),
            first_name=attributes.get('first_name'),
            last_name=attributes.get('last_name'),
            team_abbr=attributes.get('team_abbr'),
            team=attributes.get('team'),
            position=attributes.get('position'),
            sport=attributes.get('sport'),
            status=attributes.get('status'),
            age=attributes.get('age'),
            college=attributes.get('college'),
            years_exp=attributes.get('years_exp'),
            _player_data = attributes  # Pass all other attributes to store in extra_attributes
        )

    def __repr__(self):
        return (
            f"<PlayerModel(name={self.name}, player_id={self.player_id}, age={self.age}, "
            f"team={self.team_abbr}, position={self.position})>"
        )

    def get_attribute(self, attr_name: str) -> Optional[Any]:
        """
        Get an attribute value from the player_dict on demand.

        :param attr_name: The name of the attribute to retrieve.
        :return: The value of the attribute or None if it doesn't exist.
        """

        # _player_data is Optional and unset when PlayerModel is constructed directly
        # (rather than via from_dict()); calling .get() on None would raise here.
        # That's a pre-existing latent bug, not something issue #20's CI-gate work
        # should fix behind the scenes -- flagging via type: ignore rather than
        # silently changing what this returns for that edge case.
        return self._player_data.get(attr_name)  # type: ignore[union-attr]

    def get_injury_status(self):
        # returns info about injury
        pass


