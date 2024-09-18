# example_advanced.py
from sleeper_api.endpoints.draft_endpoint import DraftEndpoint
from sleeper_api.client import SleeperClient

# Initialize the API client
client = SleeperClient()

# Create a DraftEndpoint instance
draft_endpoint = DraftEndpoint(client)

# Fetch draft picks by draft ID
draft_picks = draft_endpoint.get_draft_picks(draft_id='1124826302797624320')

# Display first 12 draft picks
for pick in draft_picks[:12]:
    print(f"Pick Number: {pick.pick_no}, Player: {pick.player_name}")
