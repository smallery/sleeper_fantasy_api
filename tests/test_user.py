import pytest
from sleeper_fantasy_api.sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_fantasy_api.sleeper_api.models.user import UserModel
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

@pytest.fixture
def mock_client():
    return MockClient()

@pytest.fixture
def user_resource(mock_client):
    return UserEndpoint(mock_client)

def test_get_user_by_user_id(user_resource):
    user = user_resource.get_user(user_id="12345")
    assert isinstance(user, UserModel)
    assert user.username == "test_user"
    assert user.user_id == "12345678"
    assert user.display_name == "test_user"
    assert user.avatar == "cc12ec49965eb7856f84d71cf85306af"

def test_get_user_by_username(user_resource):
    user = user_resource.get_user(username="test_user")
    assert isinstance(user, UserModel)
    assert user.username == "test_user"
    assert user.user_id == "12345678"
    assert user.display_name == "test_user"
    assert user.avatar == "cc12ec49965eb7856f84d71cf85306af"

def test_get_user_missing_both_params(user_resource):
    with pytest.raises(SleeperAPIError, match="You must provide either user_id or username."):
        user_resource.get_user()

def test_get_user_not_found(user_resource):
    with pytest.raises(SleeperAPIError, match="User not found"):
        user_resource.get_user(user_id="nonexistent")
