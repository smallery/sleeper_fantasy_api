import unittest
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.models.user import UserModel
from sleeper_api.exceptions import SleeperAPIError

class MockClient:
    """A mock client to simulate API responses."""
    def get(self, endpoint):
        if "12345" in endpoint or "test_user" in endpoint:
            return {
                "username": "test_user",
                "user_id": "12345678",
                "display_name": "test_user",
                "avatar": "cc12ec49965eb7856f84d71cf85306af"
            }
        else:
            raise SleeperAPIError("User not found")

class TestUserEndpoint(unittest.TestCase):

    def setUp(self):
        self.mock_client = MockClient()
        self.user_resource = UserEndpoint(self.mock_client)

    def test_get_user_by_user_id(self):
        user = self.user_resource.get_user(user_id="12345")
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.username, "test_user")
        self.assertEqual(user.user_id, "12345678")
        self.assertEqual(user.display_name, "test_user")
        self.assertEqual(user.avatar, "cc12ec49965eb7856f84d71cf85306af")

    def test_get_user_by_username(self):
        user = self.user_resource.get_user(username="test_user")
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.username, "test_user")
        self.assertEqual(user.user_id, "12345678")
        self.assertEqual(user.display_name, "test_user")
        self.assertEqual(user.avatar, "cc12ec49965eb7856f84d71cf85306af")

    def test_get_user_missing_both_params(self):
        with self.assertRaises(SleeperAPIError) as context:
            self.user_resource.get_user()
        self.assertEqual(str(context.exception), "You must provide either user_id or username.")

    def test_get_user_not_found(self):
        with self.assertRaises(SleeperAPIError) as context:
            self.user_resource.get_user(user_id="nonexistent")
        self.assertEqual(str(context.exception), "User not found")

if __name__ == '__main__':
    unittest.main()
