from sleeper_api import SleeperClient
from sleeper_api.endpoints.player_endpoint import PlayerEndpoint

def print_search_results(criteria, description):
    """Helper function to search and print the number of players matching the criteria."""
    players = player_endpoint.search_players(criteria)
    print(f'{description} Returns {len(players)} players.')

# Initialize the API client and player endpoint
client = SleeperClient()
player_endpoint = PlayerEndpoint(client)

# BASIC USAGE:
print_search_results({"position": "QB"}, "Basic Criteria 1 (Quarterbacks)")
print_search_results({"age": 24}, "Basic Criteria 2 (24 years old)")

# MULTIPLE CONDITIONS (AND logic by default)
print_search_results({"position": "QB", "age": 24}, "Multiple Conditions Criteria 1 (QB and 24 years old)")
print_search_results({"team": "SF", "age": {">": 25}}, "Multiple Conditions Criteria 2 (Team SF and > 25 years old)")

# USING COMPARISON OPERATORS
print_search_results({"age": {">": 22, "<=": 30}}, "Comparison Criteria 1 (Age > 22 and <= 30)")
print_search_results({"position": {"!=": "WR"}}, "Comparison Criteria 2 (Not Wide Receivers)")

# LOGICAL GROUPING WITH AND:
and_criteria_1 = {"AND": [{"position": "QB"}, {"age": {">=": 24, "<=": 30}}]}
and_criteria_2 = {"AND": [{"team": "SF"}, {"age": {"<": 25}}]}
print_search_results(and_criteria_1, "AND Criteria 1 (QB and Age >= 24 <= 30)")
print_search_results(and_criteria_2, "AND Criteria 2 (Team SF and Age < 25)")

# LOGICAL GROUPING WITH OR:
or_criteria_1 = {"OR": [{"team": "SF"}, {"team": "NE"}, {"team_abbr": "SF"}, {"team_abbr": "NE"}]}
or_criteria_2 = {"OR": [{"position": "QB"}, {"age": {">": 30}}]}
print_search_results(or_criteria_1, "OR Criteria 1 (Team SF or NE)")
print_search_results(or_criteria_2, "OR Criteria 2 (QB or Age > 30)")

# COMBINING AND and OR OPERATORS:
combined_criteria_1 = {
    "AND": [
        {"position": "QB"},
        {"OR": [{"team": "SF"}, {"team": "NE"}]}
    ]
}
combined_criteria_2 = {
    "AND": [
        {"position": {"!=": "WR"}},
        {"OR": [{"age": {"<": 25}}, {"years_exp": {">": 3}}]}
    ]
}
print_search_results(combined_criteria_1, "Logical Combination Criteria 1 (QB and (Team SF or NE))")
print_search_results(combined_criteria_2, "Logical Combination Criteria 2 (Not WR and (Age < 25 or Exp > 3 years))")

# MEMBERSHIP OPERATER USAGE:
print_search_results({"age": {"in": [22, 24, 26]}}, "Membership Criteria 1 (Age 22, 24, or 26)")
print_search_results({"position": {"not in": ["QB", "WR", "TE"]}}, "Membership Criteria 2 (Not QB, WR, or TE)")

# ADVANCED NESTED LOGIC:
advanced_criteria_1 = {
    "AND": [
        {"OR": [{"position": "QB"}, {"position": "RB"}]},
        {"OR": [{"age": {">": 24}}, {"team": {"in": ["SF", "NE"]}}]}
    ]
}
advanced_criteria_2 = {
    "AND": [
        {"position": {"not in": ["WR", "TE"]}},
        {"age": {">=": 21, '<=': 32}}
    ]
}
print_search_results(advanced_criteria_1, "Advanced Nested Criteria 1 ((QB or RB) and (Age > 24 or Team SF/NE))")
print_search_results(advanced_criteria_2, "Advanced Nested Criteria 2 (Not WR/TE and Age >= 21 <= 32)")
