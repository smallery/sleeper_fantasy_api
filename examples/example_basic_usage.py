import argparse
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.client import SleeperClient

def main(username):
    # Initialize the API client
    client = SleeperClient()

    # Create a UserEndpoint instance
    user_endpoint = UserEndpoint(client)

    # Fetch user data by user ID
    user = user_endpoint.get_user(username=username)

    # Print out user information
    print(f"Username: {user.username}")
    print(f"User ID: {user.user_id}")
    print(f"Display Name: {user.display_name}")
    print(f"Avatar URL: {user.avatar}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and display user information from the Sleeper API.")
    parser.add_argument('-u', '--username', type=str, required=True, help='The username of the Sleeper user to fetch information for.')
    args = parser.parse_args()
    main(args.username)
