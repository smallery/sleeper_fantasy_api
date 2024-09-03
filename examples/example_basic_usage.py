# example_basic_usage.py
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.client import SleeperClient

# Initialize the API client
client = SleeperClient()

# Create a UserEndpoint instance
user_endpoint = UserEndpoint(client)

# Fetch user data by user ID
user = user_endpoint.get_user(username="JohnDoe")

# Print out user information
print(f"Username: {user.username}")
print(f"User ID: {user.user_id}")
print(f"Display Name: {user.display_name}")
print(f"Avatar URL: {user.avatar}")
