"""
This module provides the `NFLEndpoint` class for interacting
with NFL-specific undocumented API endpoints of the Sleeper API.

Note: These endpoints are undocumented and may change without notice.
"""
import logging
from datetime import datetime
from typing import List, Literal, Optional, Union, overload

from ..exceptions import SleeperAPIError
from ..models.schedule import NFLScheduleModel
from ..models.team_depth_chart import TeamDepthChartModel

logger = logging.getLogger(__name__)

# Sleeper only has schedule data from 2009 to present
MIN_SCHEDULE_YEAR = 2009


class NFLEndpoint:
    """
    NFL endpoint class for undocumented NFL-specific Sleeper API endpoints.

    Provides access to:
    - Team depth charts
    - NFL schedules (regular season and postseason)

    Every method's ``convert_results`` parameter defaults to the owning
    `SleeperClient`'s `convert_results` setting when omitted (``None``) --
    see issue #24. Pass it explicitly to override that default for a single
    call.

    Note: These are undocumented endpoints and may change without notice.
    """

    def __init__(self, client):
        """
        Initialize the NFL endpoint.

        Args:
            client: SleeperClient instance.
        """
        self.client = client

    @overload
    def get_team_depth_chart(self, team: str, convert_results: Literal[True]) -> TeamDepthChartModel: ...
    @overload
    def get_team_depth_chart(self, team: str, convert_results: Literal[False]) -> dict: ...
    @overload
    def get_team_depth_chart(
        self, team: str, convert_results: Optional[bool] = None
    ) -> Union[TeamDepthChartModel, dict]: ...

    def get_team_depth_chart(
        self,
        team: str,
        convert_results: Optional[bool] = None
    ) -> Union[TeamDepthChartModel, dict]:
        """
        Fetch the depth chart for a specific NFL team.

        Uses an undocumented Sleeper endpoint to get current depth chart data.
        The depth chart shows players organized by position with depth ordering
        (starter, backup, etc.).

        Args:
            team: NFL team abbreviation (e.g., 'SF', 'KC', 'GB', 'NE')
            convert_results: If True, return TeamDepthChartModel. If False, return raw dict.
                If omitted, uses the owning client's `convert_results` default.

        Returns:
            TeamDepthChartModel if convert_results=True, otherwise dict

        Raises:
            SleeperAPIError: If the API request fails
            ValueError: If team abbreviation is invalid

        Example:
            >>> nfl = NFLEndpoint(client)
            >>> depth_chart = nfl.get_team_depth_chart('SF')
            >>> print(depth_chart.qb)  # List of QB player IDs in depth order
            ['1234', '5678']
        """
        if not team or not isinstance(team, str):
            raise ValueError("Team abbreviation must be a non-empty string")

        if convert_results is None:
            convert_results = self.client.convert_results

        # Team abbreviations are typically 2-3 uppercase letters
        team = team.upper()

        endpoint = f"players/nfl/{team}/depth_chart"

        try:
            depth_chart_data = self.client.get(endpoint)
        except SleeperAPIError as e:
            logger.error(f"Failed to fetch depth chart for team {team}: {e}")
            raise

        if not convert_results:
            return depth_chart_data

        return TeamDepthChartModel.from_dict(depth_chart_data, team=team)

    @overload
    def get_schedule(
        self, year: int, postseason: bool = False, *, convert_results: Literal[True]
    ) -> NFLScheduleModel: ...
    @overload
    def get_schedule(
        self, year: int, postseason: bool, convert_results: Literal[True]
    ) -> NFLScheduleModel: ...
    @overload
    def get_schedule(
        self, year: int, postseason: bool = False, *, convert_results: Literal[False]
    ) -> List[dict]: ...
    @overload
    def get_schedule(
        self, year: int, postseason: bool, convert_results: Literal[False]
    ) -> List[dict]: ...
    @overload
    def get_schedule(
        self, year: int, postseason: bool = False, convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]: ...

    def get_schedule(
        self,
        year: int,
        postseason: bool = False,
        convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]:
        """
        Fetch the NFL schedule for a specific season.

        Uses an undocumented Sleeper endpoint to get schedule data.
        Note: Sleeper only has schedule data from 2009 to present.

        Args:
            year: NFL season year (must be between 2009 and current year)
            postseason: If True, fetch postseason schedule. If False, fetch regular season.
            convert_results: If True, return NFLScheduleModel. If False, return raw list.
                If omitted, uses the owning client's `convert_results` default.

        Returns:
            NFLScheduleModel if convert_results=True, otherwise List[dict]

        Raises:
            SleeperAPIError: If the API request fails
            ValueError: If year is outside valid range (2009 to present)

        Example:
            >>> nfl = NFLEndpoint(client)
            >>> schedule = nfl.get_schedule(2023, postseason=False)
            >>> week_1_games = schedule.get_games_by_week(1)
            >>> sf_games = schedule.get_games_by_team('SF')
        """
        current_year = datetime.now().year

        if convert_results is None:
            convert_results = self.client.convert_results

        # Validate year
        if year < MIN_SCHEDULE_YEAR:
            raise ValueError(
                f"Year must be {MIN_SCHEDULE_YEAR} or later. "
                f"Sleeper only has schedule data from {MIN_SCHEDULE_YEAR} to present."
            )

        if year > current_year:
            raise ValueError(
                f"Year cannot be in the future. Current year is {current_year}."
            )

        # Determine season type
        season_type = "post" if postseason else "regular"
        endpoint = f"schedule/nfl/{season_type}/{year}"

        try:
            schedule_data = self.client.get(endpoint)
        except SleeperAPIError as e:
            logger.error(f"Failed to fetch {season_type} schedule for {year}: {e}")
            raise

        if not convert_results:
            return schedule_data

        return NFLScheduleModel.from_list(schedule_data, year=year, season_type=season_type)

    @overload
    def get_regular_season_schedule(self, year: int, convert_results: Literal[True]) -> NFLScheduleModel: ...
    @overload
    def get_regular_season_schedule(self, year: int, convert_results: Literal[False]) -> List[dict]: ...
    @overload
    def get_regular_season_schedule(
        self, year: int, convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]: ...

    def get_regular_season_schedule(
        self,
        year: int,
        convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]:
        """
        Convenience method to fetch the regular season schedule.

        Args:
            year: NFL season year
            convert_results: If True, return NFLScheduleModel. If False, return raw list.
                If omitted, uses the owning client's `convert_results` default.

        Returns:
            NFLScheduleModel if convert_results=True, otherwise List[dict]
        """
        return self.get_schedule(year, postseason=False, convert_results=convert_results)

    @overload
    def get_postseason_schedule(self, year: int, convert_results: Literal[True]) -> NFLScheduleModel: ...
    @overload
    def get_postseason_schedule(self, year: int, convert_results: Literal[False]) -> List[dict]: ...
    @overload
    def get_postseason_schedule(
        self, year: int, convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]: ...

    def get_postseason_schedule(
        self,
        year: int,
        convert_results: Optional[bool] = None
    ) -> Union[NFLScheduleModel, List[dict]]:
        """
        Convenience method to fetch the postseason schedule.

        Args:
            year: NFL season year
            convert_results: If True, return NFLScheduleModel. If False, return raw list.
                If omitted, uses the owning client's `convert_results` default.

        Returns:
            NFLScheduleModel if convert_results=True, otherwise List[dict]
        """
        return self.get_schedule(year, postseason=True, convert_results=convert_results)
