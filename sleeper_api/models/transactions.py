from typing import List, Dict, Optional, Union, Any

class DraftPick:
    def __init__(self, season: str, round: int, roster_id: int, previous_owner_id: int, owner_id: int):
        self.season = season
        self.round = round
        self.roster_id = roster_id
        self.previous_owner_id = previous_owner_id
        self.owner_id = owner_id

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int]]) -> 'DraftPick':
        return cls(
            season=data['season'],
            round=data['round'],
            roster_id=data['roster_id'],
            previous_owner_id=data['previous_owner_id'],
            owner_id=data['owner_id']
        )

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {
            'season': self.season,
            'round': self.round,
            'roster_id': self.roster_id,
            'previous_owner_id': self.previous_owner_id,
            'owner_id': self.owner_id
        }

    def __repr__(self):
        return (f"<DraftPick(season={self.season}, round={self.round}, roster_id={self.roster_id}, "
                f"previous_owner_id={self.previous_owner_id}, owner_id={self.owner_id})>")


class WaiverBudgetTransfer:
    def __init__(self, sender: int, receiver: int, amount: int):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'WaiverBudgetTransfer':
        return cls(
            sender=data['sender'],
            receiver=data['receiver'],
            amount=data['amount']
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount
        }

    def __repr__(self):
        return f"<WaiverBudgetTransfer(sender={self.sender}, receiver={self.receiver}, amount={self.amount})>"


class TransactionsModel:
    def __init__(
        self,
        transaction_type: str,
        transaction_id: str,
        status_updated: int,
        status: str,
        roster_ids: List[int],
        leg: int,
        draft_picks: Optional[List[DraftPick]] = None,
        creator: Optional[str] = None,
        created: Optional[int] = None,
        consenter_ids: Optional[List[int]] = None,
        waiver_budget: Optional[List[WaiverBudgetTransfer]] = None,
        drops: Optional[Dict[str, int]] = None,
        adds: Optional[Dict[str, int]] = None,
    ):
        
        # Add type validation checks here
        if not isinstance(transaction_type, str):
            raise ValueError(f"Invalid type for 'transaction_type': expected str, got {type(transaction_type).__name__}")
        if not isinstance(transaction_id, str):
            raise ValueError(f"Invalid type for 'transaction_id': expected str, got {type(transaction_id).__name__}")
        if not isinstance(status_updated, int):
            raise ValueError(f"Invalid type for 'status_updated': expected int, got {type(status_updated).__name__}")
        if not isinstance(status, str):
            raise ValueError(f"Invalid type for 'status': expected str, got {type(status).__name__}")
        if not isinstance(roster_ids, list) or not all(isinstance(rid, int) for rid in roster_ids):
            raise ValueError(f"Invalid type for 'roster_ids': expected List[int], got {type(roster_ids).__name__}")
        if not isinstance(leg, int):
            raise ValueError(f"Invalid type for 'leg': expected int, got {type(leg).__name__}")

        self.transaction_type = transaction_type
        self.transaction_id = transaction_id
        self.status_updated = status_updated
        self.status = status
        self.roster_ids = roster_ids
        self.leg = leg
        self.draft_picks = draft_picks or []
        self.creator = creator
        self.created = created
        self.consenter_ids = consenter_ids or []
        self.waiver_budget = waiver_budget or []
        self.drops = drops or {}
        self.adds = adds or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionsModel':
        draft_picks = [DraftPick.from_dict(dp) for dp in data.get('draft_picks', [])]
        waiver_budget = [WaiverBudgetTransfer.from_dict(wb) for wb in data.get('waiver_budget', [])]

        return cls(
            transaction_type=data['type'],
            transaction_id=data['transaction_id'],
            status_updated=data['status_updated'],
            status=data['status'],
            roster_ids=data['roster_ids'],
            leg=data['leg'],
            draft_picks=draft_picks,
            creator=data.get('creator'),
            created=data.get('created'),
            consenter_ids=data.get('consenter_ids', []),
            waiver_budget=waiver_budget,
            drops=data.get('drops'),
            adds=data.get('adds'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.transaction_type,
            'transaction_id': self.transaction_id,
            'status_updated': self.status_updated,
            'status': self.status,
            'roster_ids': self.roster_ids,
            'leg': self.leg,
            'draft_picks': [dp.to_dict() for dp in self.draft_picks],
            'creator': self.creator,
            'created': self.created,
            'consenter_ids': self.consenter_ids,
            'waiver_budget': [wb.to_dict() for wb in self.waiver_budget],
            'drops': self.drops,
            'adds': self.adds,
        }

    def __repr__(self):
        return (f"<TransactionsModel(transaction_id={self.transaction_id}, type={self.transaction_type}, "
                f"status={self.status}, roster_ids={self.roster_ids}, leg={self.leg})>")
