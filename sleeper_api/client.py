"""
This module provides the `SleeperClient` class for interacting with the Sleeper API.

The `SleeperClient` class facilitates making API calls to various endpoints of the Sleeper API.
It supports handling HTTP requests and responses, including managing authentication
headers and timeouts.

"""
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .config import BASE_URL
from .exceptions import SleeperAPIError, RateLimitError

logger = logging.getLogger(__name__)

class SleeperClient:
    """
    SleeperClient will be used to perform API calls across multiple endpoints.
    """
    def __init__(
        self,
        api_key = None,
        timeout = 10,
        max_retries = 3,
        initial_backoff = 1.0
    ):
        """
        Initialize the SleeperClient.

        :param api_key: Optional API key for authentication (if required).
        :param timeout: Timeout for requests in seconds.
        :param max_retries: Maximum retry attempts for rate-limited requests.
        :param initial_backoff: Initial backoff time in seconds for exponential backoff.
        """
        self.base_url = BASE_URL
        self.api_key = api_key # not currently required
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.session = self._create_session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.

        Returns:
            Configured requests.Session with automatic retry for server errors.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _handle_response(self, response):
        """
        Handle the API response.

        :param response: The HTTP response object.
        :return: The parsed JSON data or raise an error.
        """
        if response.status_code == 404:
            return None  # Not an error, just missing resource

        if not response.ok:
            raise SleeperAPIError(
                f"Error {response.status_code}: {response.text}",
                status_code=response.status_code
            )
        try:
            return response.json()
        except ValueError as exc:
            raise SleeperAPIError("Invalid JSON response received") from exc

    def _request(self, method, endpoint, params=None, data=None):
        """
        Make a request to the Sleeper API with retry logic.

        :param method: HTTP method (GET, POST, etc.).
        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :param data: Request payload for POST/PUT requests.
        :return: Parsed JSON response.
        """
        url = f'{self.base_url}{endpoint}'
        backoff = self.initial_backoff

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout
                )

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limited, retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        continue
                    raise RateLimitError("Rate limit exceeded after all retries")

                return self._handle_response(response)

            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    logger.warning(f"Request failed, retrying in {backoff}s: {exc}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise SleeperAPIError(f"Request failed after {self.max_retries} retries: {exc}") from exc

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
