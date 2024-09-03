from typing import Dict, List
from ..models.league import LeagueModel
from ..models.roster import RosterModel
from ..models.matchups import MatchupModel
from ..models.brackets import BracketModel
from ..models.transactions import TransactionsModel
from ..models.traded_picks import TradedDraftPicksModel
from .user_endpoint import UserEndpoint
from ..config import CONVERT_RESULTS

class LeagueEndpoint:
    def __init__(self, client):
        self.client = client

    def get_league(self, league_id: str) -> LeagueModel:
        """
        Retrieve a specific league by its ID.
        """
        endpoint = f"league/{league_id}"
        league_data = self.client.get(endpoint)
        return LeagueModel.from_json(league_data)

    def get_rosters(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the rosters for a given league.
        """
        endpoint = f"league/{league_id}/rosters"
        rosters_json = self.client.get(endpoint)
        if not convert_results:
            return rosters_json

        return [RosterModel.from_dict(roster_data) for roster_data in rosters_json]

    def get_users(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the users in a given league.
        Returns a list of users. 
            - If convert_results = False, this will be the raw JSON.
            - If convert_results = True, then this will be a list of user model objects
        """
        endpoint = f"league/{league_id}/users"
        users_json = self.client.get(endpoint)
        
        if not convert_results:
            return users_json
            
        # note: the username will be missing from these user records, this can be retrieved
        user_endpoint = UserEndpoint(self.client)
        return [user_endpoint.get_user(user.get("user_id")) for user in users_json]
            

    def get_matchups(self, league_id: str, week: int, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the matchups for a given league and week.
        """

        # TO DO: combined matchups into a single model so you can find both teams in the same matchup object
        endpoint = f"league/{league_id}/matchups/{week}"
        matchup_json = self.client.get(endpoint)

        if not convert_results:
            return matchup_json
        
        return [MatchupModel.from_dict(matchup_data) for matchup_data in matchup_json]

    def get_winners_bracket(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the winner's bracket for a given league.
        """
        endpoint = f"league/{league_id}/winners_bracket"
        bracket_json = self.client.get(endpoint)
        
        if not convert_results:
            return bracket_json
        
        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    def get_losers_bracket(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve the loser's bracket for a given league.
        """
        endpoint = f"league/{league_id}/losers_bracket"
        bracket_json = self.client.get(endpoint)
        
        if not convert_results:
            return bracket_json
        
        return [BracketModel.from_dict(bracket_data) for bracket_data in bracket_json]

    def get_transactions(self, league_id: str, week: int, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve transactions for a given league. Filter by week.
        """
        endpoint = f"league/{league_id}/transactions/{week}"
        transactions_json = self.client.get(endpoint)

        if not convert_results:
            return transactions_json
        
        return [TransactionsModel.from_dict(transaction_data) for transaction_data in transactions_json]

    def get_traded_picks(self, league_id: str, convert_results = CONVERT_RESULTS) -> List[Dict]:
        """
        Retrieve traded picks for a given league.
        """
        endpoint = f"league/{league_id}/traded_picks"
        traded_picks_json = self.client.get(endpoint)

        if not convert_results:
            return traded_picks_json
        
        return [TradedDraftPicksModel.from_dict(traded_pick_data) for traded_pick_data in traded_picks_json]