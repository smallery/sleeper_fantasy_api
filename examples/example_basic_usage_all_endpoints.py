from sleeper_api.client import SleeperClient
from sleeper_api.endpoints.user_endpoint import UserEndpoint
from sleeper_api.endpoints.draft_endpoint import DraftEndpoint
from sleeper_api.endpoints.league_endpoint import LeagueEndpoint
from sleeper_api.endpoints.player_endpoint import PlayerEndpoint


# Initialize the API client
client = SleeperClient()

# Create a UserEndpoint instance
user_endpoint = UserEndpoint(client)

# fetch user information
user = user_endpoint.get_user('jcole00')

print(f"User ID: {user.user_id}")
print(f"Username: {user.username}\n")

# populate the leagues list
user_endpoint.fetch_nfl_leagues(user, season=2024)
print(f'{user.username} was in {len(user.nfl_leagues)} league(s) in 2024')

# create league endpoint
league_endpoint = LeagueEndpoint(client)

# fetch the first league out of all leagues
league = league_endpoint.get_league(user.nfl_leagues[0].league_id)
print(f'The league was called {league.name} and was a {league.season_type} fantasy league for the {league.sport}')

league_users = league_endpoint.get_users(league.league_id)
print(f'There were {len(league_users)} users in the league.\n')

# create draft endpoint
draft_endpoint = DraftEndpoint(client)

draft = draft_endpoint.get_draft_by_id(league.draft_id)
user_draft_pick = draft.draft_order[user.user_id]
print(f'{user.username} had pick {user_draft_pick} in the draft (draft_id: {draft.draft_id})')

draft_picks = draft_endpoint.get_draft_picks(draft.draft_id)

user_first_round_draft_pick = draft_picks[user_draft_pick - 1]
print(f'With their first round pick in the draft, {user.username} selected {user_first_round_draft_pick.player_name}.\n')

### GET PLAYER INFORMATION
#setup player endpoint
player_endpoint = PlayerEndpoint(client)

print(f'Additional information on {user.username} first round draft pick...')
player = player_endpoint.get_player(user_first_round_draft_pick.player_id)
print(f'Player:   {player.name}')
print(f'Age:      {player.age}')
print(f'Position: {player.position}')
print(f'Team:     {player.team_abbr}')
print(f'Status:   {player.status}')
# get specific attribute from the player that's not included in base class
print(f'Weight:   {player.get_attribute("weight")}')


### PRINT OUT TEAM (ROSTER) INFORMATION

print('')
print(f"Here is a snapshot of {user.username}'s current team:")

# grab all league rosters
league_rosters = league_endpoint.get_rosters(league.league_id)
# get specific user's roster
user_roster = next((roster for roster in league_rosters if roster.owner_id == user.user_id), None)

# print our starters and bench, lookup players to get full info and not just player_id
print("Starters:")
for starter_id in user_roster.starters:
    starter_player = player_endpoint.get_player(starter_id)
    print(f'Position: {starter_player.position:<5} | Player Name: {starter_player.name:<20} | Team: {starter_player.team_abbr:<5} | Age: {starter_player.age}')

print("\nBench:")
for bench_id in user_roster.bench:
    bench_player = player_endpoint.get_player(bench_id)
    print(f'Position: {bench_player.position:<5} | Player Name: {bench_player.name:<20} | Team: {bench_player.team_abbr:<5} | Age: {bench_player.age}')
