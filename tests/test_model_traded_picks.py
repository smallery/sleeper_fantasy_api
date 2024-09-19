import unittest
from sleeper_api.models.traded_picks import TradedPickModel, TradedDraftPicksModel

class TestTradedPick(unittest.TestCase):

    def setUp(self):
        self.valid_pick_data = {
            "season": "2019",
            "round": 5,
            "roster_id": 1,
            "previous_owner_id": 1,
            "owner_id": 2
        }
        self.valid_pick_data_2 = {
            "season": "2020",
            "round": 3,
            "roster_id": 2,
            "previous_owner_id": 2,
            "owner_id": 1
        }

    def test_traded_pick_initialization(self):
        pick = TradedPickModel.from_dict(self.valid_pick_data)

        self.assertEqual(pick.season, "2019")
        self.assertEqual(pick.round, 5)
        self.assertEqual(pick.roster_id, 1)
        self.assertEqual(pick.previous_owner_id, 1)
        self.assertEqual(pick.owner_id, 2)

    def test_traded_pick_to_dict(self):
        pick = TradedPickModel.from_dict(self.valid_pick_data)
        pick_dict = pick.to_dict()

        self.assertEqual(pick_dict, self.valid_pick_data)

    def test_traded_pick_repr(self):
        pick = TradedPickModel.from_dict(self.valid_pick_data)
        expected_repr = "<TradedPickModel(season=2019, round=5, roster_id=1, previous_owner_id=1, owner_id=2)>"
        self.assertEqual(repr(pick), expected_repr)

    def test_traded_draft_picks_model_initialization(self):
        picks_data = [self.valid_pick_data, self.valid_pick_data_2]
        traded_picks_model = TradedDraftPicksModel.from_list(picks_data)

        self.assertEqual(len(traded_picks_model.traded_picks), 2)
        self.assertEqual(traded_picks_model.traded_picks[0].season, "2019")
        self.assertEqual(traded_picks_model.traded_picks[1].season, "2020")

    def test_traded_draft_picks_model_to_list(self):
        picks_data = [self.valid_pick_data, self.valid_pick_data_2]
        traded_picks_model = TradedDraftPicksModel.from_list(picks_data)
        picks_list = traded_picks_model.to_list()

        self.assertEqual(picks_list, picks_data)

    def test_traded_draft_picks_model_repr(self):
        picks_data = [self.valid_pick_data, self.valid_pick_data_2]
        traded_picks_model = TradedDraftPicksModel.from_list(picks_data)

        expected_repr = "<TradedDraftPicksModel(traded_picks=2 picks)>"
        self.assertEqual(repr(traded_picks_model), expected_repr)

    def test_traded_pick_invalid_data(self):
        # Test invalid data for TradedPick
        invalid_pick_data = {
            "season": 2019,  # Should be a string, not an int
            "round": 5,
            "roster_id": 1,
            "previous_owner_id": 1,
            "owner_id": 2
        }

        with self.assertRaises(ValueError):
            TradedPickModel.from_dict(invalid_pick_data)

if __name__ == '__main__':
    unittest.main()
