import unittest
from sleeper_api.models.transactions import TransactionsModel, DraftPick, WaiverBudgetTransfer

class TestTransactionsModel(unittest.TestCase):

    def setUp(self):
        self.valid_transaction_data = {
            "type": "trade",
            "transaction_id": "123456",
            "status_updated": 1632968400,
            "status": "complete",
            "roster_ids": [1, 2],
            "leg": 1,
            "draft_picks": [
                {
                    "season": "2022",
                    "round": 1,
                    "roster_id": 1,
                    "previous_owner_id": 2,
                    "owner_id": 1
                }
            ],
            "creator": "user123",
            "created": 1632960000,
            "consenter_ids": [1, 2],
            "waiver_budget": [
                {
                    "sender": 1,
                    "receiver": 2,
                    "amount": 100
                }
            ],
            "drops": {
                "player1": 1
            },
            "adds": {
                "player2": 2
            }
        }

        self.invalid_transaction_data = {
            "type": "trade",
            "transaction_id": "123456",
            "status_updated": 1632968400,
            "status": "complete",
            "roster_ids": "invalid_roster_ids",  # Invalid type: should be List[int]
            "leg": 1,
        }

    def test_transactions_model_initialization(self):
        transaction = TransactionsModel.from_dict(self.valid_transaction_data)

        self.assertEqual(transaction.transaction_type, "trade")
        self.assertEqual(transaction.transaction_id, "123456")
        self.assertEqual(transaction.status_updated, 1632968400)
        self.assertEqual(transaction.status, "complete")
        self.assertEqual(transaction.roster_ids, [1, 2])
        self.assertEqual(transaction.leg, 1)
        self.assertEqual(len(transaction.draft_picks), 1)
        self.assertEqual(transaction.creator, "user123")
        self.assertEqual(transaction.created, 1632960000)
        self.assertEqual(transaction.consenter_ids, [1, 2])
        self.assertEqual(len(transaction.waiver_budget), 1)
        self.assertEqual(transaction.drops["player1"], 1)
        self.assertEqual(transaction.adds["player2"], 2)

    def test_transactions_model_to_dict(self):
        transaction = TransactionsModel.from_dict(self.valid_transaction_data)
        transaction_dict = transaction.to_dict()

        self.assertEqual(transaction_dict, self.valid_transaction_data)

    def test_draft_pick_initialization(self):
        draft_pick_data = {
            "season": "2022",
            "round": 1,
            "roster_id": 1,
            "previous_owner_id": 2,
            "owner_id": 1
        }
        draft_pick = DraftPick.from_dict(draft_pick_data)

        self.assertEqual(draft_pick.season, "2022")
        self.assertEqual(draft_pick.round, 1)
        self.assertEqual(draft_pick.roster_id, 1)
        self.assertEqual(draft_pick.previous_owner_id, 2)
        self.assertEqual(draft_pick.owner_id, 1)

    def test_waiver_budget_transfer_initialization(self):
        waiver_budget_data = {
            "sender": 1,
            "receiver": 2,
            "amount": 100
        }
        waiver_transfer = WaiverBudgetTransfer.from_dict(waiver_budget_data)

        self.assertEqual(waiver_transfer.sender, 1)
        self.assertEqual(waiver_transfer.receiver, 2)
        self.assertEqual(waiver_transfer.amount, 100)

    def test_transactions_model_invalid_data(self):
        # Test invalid data for TransactionsModel
        with self.assertRaises(ValueError):
            TransactionsModel.from_dict(self.invalid_transaction_data)

if __name__ == '__main__':
    unittest.main()
