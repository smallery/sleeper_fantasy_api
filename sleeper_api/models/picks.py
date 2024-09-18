## TO DO Fix this so picks model is simpler

from typing import List, Dict, Optional, Union
from ..exceptions import SleeperAPIError

class PickMetadata:
    def __init__(
        self,
        team: str,
        status: str,
        sport: str,
        position: str,
        player_id: str,
        number: str,
        news_updated: str,
        last_name: str,
        injury_status: str,
        first_name: str
    ):
        self.team = team
        self.status = status
        self.sport = sport
        self.position = position
        self.player_id = player_id
        self.number = number
        self.news_updated = news_updated
        self.last_name = last_name
        self.injury_status = injury_status
        self.first_name = first_name

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'PickMetadata':
        return cls(
            team=data['team'],
            status=data['status'],
            sport=data['sport'],
            position=data['position'],
            player_id=data['player_id'],
            number=data['number'],
            news_updated=data['news_updated'],
            last_name=data['last_name'],
            injury_status=data['injury_status'],
            first_name=data['first_name']
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            'team': self.team,
            'status': self.status,
            'sport': self.sport,
            'position': self.position,
            'player_id': self.player_id,
            'number': self.number,
            'news_updated': self.news_updated,
            'last_name': self.last_name,
            'injury_status': self.injury_status,
            'first_name': self.first_name
        }

    def __repr__(self):
        return (f"<PickMetadata(player_id={self.player_id}, team={self.team}, "
                f"status={self.status}, position={self.position})>")

class PicksModel:
    def __init__(
        self,
        player_id: str,
        picked_by: str,
        roster_id: str,
        round: int,
        draft_slot: int,
        pick_no: int,
        metadata: PickMetadata,
        is_keeper: Optional[bool],
        draft_id: str
    ):
        
        # Type validation for important fields
        if not isinstance(player_id, str):
            raise SleeperAPIError(f"Invalid type for player_id: expected str, got {type(player_id).__name__}")
        if not isinstance(picked_by, str):
            raise SleeperAPIError(f"Invalid type for picked_by: expected str, got {type(picked_by).__name__}")
        if not isinstance(roster_id, (str,int)):
            raise SleeperAPIError(f"Invalid type for roster_id: expected str or int, got {type(roster_id).__name__}")
        if not isinstance(round, int):
            raise SleeperAPIError(f"Invalid type for round: expected int, got {type(round).__name__}")
        if not isinstance(draft_slot, int):
            raise SleeperAPIError(f"Invalid type for draft_slot: expected int, got {type(draft_slot).__name__}")
        if not isinstance(pick_no, int):
            raise SleeperAPIError(f"Invalid type for pick_no: expected int, got {type(pick_no).__name__}")
        if metadata is not None and not isinstance(metadata, PickMetadata):
            raise SleeperAPIError(f"Invalid type for metadata: expected PickMetadata, got {type(metadata).__name__}")
        if not isinstance(draft_id, str):
            raise SleeperAPIError(f"Invalid type for draft_id: expected str, got {type(draft_id).__name__}")

        self.player_id = player_id
        self.picked_by = picked_by
        self.roster_id = str(roster_id)
        self.round = round
        self.draft_slot = draft_slot
        self.pick_no = pick_no
        self.metadata = metadata
        self.is_keeper = is_keeper
        self.draft_id = draft_id

    @property
    def player_name(self) -> str:
        """Combines the first and last name of the player."""
        return f"{self.metadata.first_name} {self.metadata.last_name}"

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int, Optional[bool], Dict[str, str]]]):
        metadata = PickMetadata.from_dict(data['metadata'])
        return cls(
            player_id=data['player_id'],
            picked_by=data['picked_by'],
            roster_id=data['roster_id'],
            round=data['round'],
            draft_slot=data['draft_slot'],
            pick_no=data['pick_no'],
            metadata=metadata,
            is_keeper=data['is_keeper'],
            draft_id=data['draft_id']
        )

    def to_dict(self) -> Dict[str, Union[str, int, Optional[bool], Dict[str, str]]]:
        return {
            'player_id': self.player_id,
            'picked_by': self.picked_by,
            'roster_id': self.roster_id,
            'round': self.round,
            'draft_slot': self.draft_slot,
            'pick_no': self.pick_no,
            'metadata': self.metadata.to_dict(),
            'is_keeper': self.is_keeper,
            'draft_id': self.draft_id
        }
    @classmethod
    def from_list(cls, data_list: List[Dict]) -> List['PicksModel']:
        """
        Create a list of PicksModel instances from a list of dictionaries.
        """
        return [cls.from_dict(data) for data in data_list]
    
    def __repr__(self):
        return (f"<Pick(player_id={self.player_id}, player_name={self.player_name}, "
                f"round={self.round}, picked_by={self.picked_by}, "
                f"pick_no={self.pick_no}, roster_id={self.roster_id})>")