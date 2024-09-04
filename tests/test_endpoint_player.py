import unittest
from unittest.mock import MagicMock, patch
from sleeper_api.endpoints.player_endpoint import PlayerEndpoint
from sleeper_api.models.player import PlayerModel
from sleeper_api.exceptions import SleeperAPIError

class TestPlayerEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = PlayerEndpoint(self.client)

    def test_get_all_players_cache_valid(self):
        # Mock valid cache
        with patch.object(self.endpoint, '_is_cache_valid', return_value=True), \
                patch.object(self.endpoint, '_load_cache', return_value={"3086": {"player_id": "3086", "first_name": "Tom", "last_name": "Brady", "team": "NE"}}):
            
            players = self.endpoint.get_all_players()
            self.assertEqual(len(players), 1)
            self.assertEqual(players[0].first_name, "Tom")
            self.assertEqual(players[0].last_name, "Brady")

    def test_get_all_players_cache_invalid(self):
        # Mock invalid cache and API response
        mock_response = {"3086": {"player_id": "3086", "first_name": "Tom", "last_name": "Brady", "team": "NE"}}
        with patch.object(self.endpoint, '_is_cache_valid', return_value=False), \
                patch.object(self.endpoint, '_save_cache'), \
                patch.object(self.client, 'get', return_value=mock_response):
            
            players = self.endpoint.get_all_players()
            self.client.get.assert_called_once_with('players/nfl')
            self.assertEqual(len(players), 1)
            self.assertEqual(players[0].first_name, "Tom")
            self.assertEqual(players[0].last_name, "Brady")

    def test_get_trending_players_add(self):
        # Mock trending data and all player data
        mock_trending = [{"player_id": "3086", "count": 50}]
        mock_all_players = {"3086": {"player_id": "3086", "first_name": "Tom", "last_name": "Brady", "team": "NE"}}

        with patch.object(self.client, 'get', return_value=mock_trending), \
                patch.object(self.endpoint, 'get_all_players', return_value=[PlayerModel.from_dict(mock_all_players["3086"])]):
            
            trending_players = self.endpoint.get_trending_players(sport="nfl", trend_type="add")
            self.assertEqual(len(trending_players), 1)
            self.assertEqual(trending_players[0].first_name, "Tom")
            self.assertEqual(trending_players[0].add_count, 50)

    def test_get_trending_players_drop(self):
        # Mock trending data and all player data
        mock_trending = [{"player_id": "3086", "count": 20}]
        mock_all_players = {"3086": {"player_id": "3086", "first_name": "Tom", "last_name": "Brady", "team": "NE"}}

        with patch.object(self.client, 'get', return_value=mock_trending), \
                patch.object(self.endpoint, 'get_all_players', return_value=[PlayerModel.from_dict(mock_all_players["3086"])]):
            
            trending_players = self.endpoint.get_trending_players(sport="nfl", trend_type="drop")
            self.assertEqual(len(trending_players), 1)
            self.assertEqual(trending_players[0].first_name, "Tom")
            self.assertEqual(trending_players[0].drop_count, 20)

    def test_get_trending_players_invalid_type(self):
        with self.assertRaises(SleeperAPIError):
            self.endpoint.get_trending_players(sport="nfl", trend_type="invalid")

    def test_search_players(self):
        # Mock player data as raw JSON dictionaries
        mock_players_json = {
            "3086": {
                "first_name": "Tom", "last_name": "Brady", "team": "NE", "position": "QB", "age": 40
            },
            "3090": {
                "first_name": "Aaron", "last_name": "Rodgers", "team": "GB", "position": "QB", "age": 38
            }
        }

        with patch.object(self.endpoint, 'get_all_players', return_value=mock_players_json):
            criteria = {"position": "QB", "age": {">": 35}}
            results = self.endpoint.search_players(criteria)

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].first_name, "Tom")
            self.assertEqual(results[1].first_name, "Aaron")


    def test_get_player(self):
        # Mock all player data
        mock_all_players = {"3086": {"player_id": "3086", "first_name": "Tom", "last_name": "Brady", "team": "NE"}}

        with patch.object(self.endpoint, 'get_all_players', return_value=[PlayerModel.from_dict(mock_all_players["3086"])]):
            player = self.endpoint.get_player("3086")
            self.assertEqual(player.first_name, "Tom")
            self.assertEqual(player.last_name, "Brady")

    def test_get_player_not_found(self):
        # Mock empty player data
        with patch.object(self.endpoint, 'get_all_players', return_value=[]):
            player = self.endpoint.get_player("invalid_id")
            self.assertIsNone(player)

if __name__ == '__main__':
    unittest.main()
