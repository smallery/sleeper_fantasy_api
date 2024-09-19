"""
This module provides the `SleeperClient` class for interacting with the Sleeper API.

The `SleeperClient` class facilitates making API calls to various endpoints of the Sleeper API.
It supports handling HTTP requests and responses, including managing authentication 
headers and timeouts.

"""
import requests
from .config import BASE_URL
from .exceptions import SleeperAPIError

class SleeperClient:
    """
    SleeperClient will be used to perform API calls across multiple endpoints.
    """
    def __init__(self, api_key = None, timeout = 10):
        """
        Initialize the SleeperClient.

        :param api_key: Optional API key for authentication (if required).
        :param timeout: Timeout for requests in seconds.
        """
        self.base_url = BASE_URL
        self.api_key = api_key # not currently required
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    def _handle_response(self, response):
        """
        Handle the API response.

        :param response: The HTTP response object.
        :return: The parsed JSON data or raise an error.
        """
        if not response.ok:
            raise SleeperAPIError(f"Error {response.status_code}: {response.text}")
        try:
            return response.json()
        except ValueError as exc:
            raise SleeperAPIError("Invalid JSON response received") from exc

    def _request(self, method, endpoint, params=None, data=None):
        """
        Make a request to the Sleeper API.
        :param method: HTTP method (GET, POST, etc.).
        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :param data: Request payload for POST/PUT requests.
        :return: Parsed JSON response.
        """
        url = f'{self.base_url}/{endpoint}'

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=data,
            timeout=self.timeout
        )

        return self._handle_response(response)

    def get(self, endpoint, params=None):
        """
        Make a GET request. Currently sleeper API only supports reading.

        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :return: Parsed JSON response.
        """
        return self._request('GET', endpoint, params=params)

    def get_base_url(self):
        "Returns the base url"
        return self.base_url
