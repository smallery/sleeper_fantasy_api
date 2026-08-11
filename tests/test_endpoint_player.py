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

    def test_get_trending_players_passes_query_params_not_hand_built_string(self):
        # get_trending_players used to interpolate lookback_hours/limit
        # directly into the endpoint path with no URL-encoding. The client's
        # get() already accepts params=, which requests encodes correctly
        # (see issue #21).
        with patch.object(self.client, 'get', return_value=[]) as mock_get, \
                patch.object(self.endpoint, 'get_all_players', return_value=[]):
            self.endpoint.get_trending_players(
                sport="nfl", trend_type="add", lookback_hours=12, limit=5
            )
            mock_get.assert_called_once_with(
                "players/nfl/trending/add",
                params={"lookback_hours": 12, "limit": 5},
            )

    def test_get_trending_players_calls_get_all_players_with_keyword_args(self):
        # Regression test for a real bug: this used to call
        # self.get_all_players(convert_results) *positionally*, but
        # get_all_players's signature is (sport='nfl', convert_results=...),
        # so the boolean landed in the `sport` slot and the real
        # convert_results argument was silently ignored. It went unnoticed
        # because get_all_players's cache-hit path never reads `sport`; a
        # cache miss would have requested players/True from the API.
        mock_trending = [{"player_id": "3086", "count": 50}]
        with patch.object(self.client, 'get', return_value=mock_trending), \
                patch.object(self.endpoint, 'get_all_players', return_value=[]) as mock_get_all:
            self.endpoint.get_trending_players(sport="nfl", trend_type="add", convert_results=True)
            mock_get_all.assert_called_once_with(sport="nfl", convert_results=True)

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
            with self.assertRaises(SleeperAPIError):
                self.endpoint.get_player("invalid_id")

if __name__ == '__main__':
    unittest.main()


class TestPoisonedPlayerCache(unittest.TestCase):
    """A cache file written by a pre-#21 version must not break get_all_players.

    Until get_trending_players() stopped passing convert_results positionally
    into `sport`, this endpoint fetched `players/True`, got a 404 (None), and
    cached it. Upgrading with such a file on disk used to raise AttributeError
    on the .items() call.
    """

    def setUp(self):
        self.client = MagicMock()
        self.endpoint = PlayerEndpoint(self.client)

    def _poison(self, value):
        import gzip
        import json
        self.endpoint.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.endpoint.cache_file, 'wt') as f:
            json.dump(value, f)

    def tearDown(self):
        if self.endpoint.cache_file.exists():
            self.endpoint.cache_file.unlink()

    def test_non_mapping_cache_is_treated_as_a_miss_and_refetched(self):
        for poison in ([], None, "nope"):
            with self.subTest(poison=poison):
                self._poison(poison)
                self.client.get.return_value = {"1234": {"player_id": "1234"}}
                players = self.endpoint.get_all_players(convert_results=False)
                self.assertEqual(players, {"1234": {"player_id": "1234"}})
                self.client.get.assert_called_with("players/nfl")

    def test_unusable_response_is_not_cached(self):
        self._poison([])
        self.client.get.return_value = None
        with self.assertRaises(SleeperAPIError):
            self.endpoint.get_all_players(convert_results=False)
        # The bad response must not have overwritten the cache with more garbage.
        self.client.get.return_value = {"1234": {"player_id": "1234"}}
        self.assertEqual(
            self.endpoint.get_all_players(convert_results=False),
            {"1234": {"player_id": "1234"}},
        )
