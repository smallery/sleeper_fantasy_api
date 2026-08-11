"""
This module provides the `SleeperClient` class for interacting with the Sleeper API.

The `SleeperClient` class facilitates making API calls to various endpoints of the Sleeper API.
It supports handling HTTP requests and responses, including managing authentication
headers and timeouts.

"""
import time
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from requests.adapters import HTTPAdapter
from .config import BASE_URL
from .exceptions import SleeperAPIError, RateLimitError

logger = logging.getLogger(__name__)

# Status codes worth retrying: 429 is Sleeper rate limiting, the 5xx set is
# transient server/gateway failure. Anything else is a real answer and is
# returned (or raised) immediately.
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Longest Retry-After this client will wait out. Beyond this, sleeping would
# block the caller for longer than any reasonable request budget (this library
# gets used inside web request handlers), so the error is raised immediately and
# the caller decides. Retrying sooner than the server asked would be worse than
# not retrying at all.
MAX_RETRY_AFTER_SECONDS = 60.0


def _parse_retry_after(value):
    """
    Parse a Retry-After header into a delay in seconds.

    Both forms in RFC 9110 are accepted: delta-seconds ("120") and an HTTP-date
    ("Wed, 21 Oct 2015 07:28:00 GMT").

    :param value: Raw header value, or None if absent.
    :return: Non-negative delay in seconds, or None if absent/unparseable.
    """
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    if retry_at is None:
        return None
    # An HTTP-date without a zone is UTC by spec.
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


class SleeperClient:
    """
    SleeperClient will be used to perform API calls across multiple endpoints.

    Retry policy: a single explicit layer in :meth:`_request` handles rate
    limits, transient 5xx responses, and transport errors with exponential
    backoff. The underlying HTTPAdapter is deliberately configured with
    ``max_retries=0`` -- when it also carried a urllib3 ``Retry`` the two layers
    multiplied, so one outage could cost (max_retries + 1) x 4 requests and tens
    of seconds of stacked sleeps.

    The session is safe to share across threads for the read-only GETs this
    client makes; the connection pool is sized to allow concurrent fan-out
    (see ``ProjectionsEndpoint.get_season_projections(max_workers=...)``).
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
        Create a requests session sized for concurrent use.

        Retries are handled entirely by :meth:`_request`, so the adapter is
        mounted with ``max_retries=0``. The pool is enlarged past urllib3's
        default of 10 so that a thread-pool fan-out over several weeks of
        projections does not serialize on connection checkout.

        Returns:
            Configured requests.Session.
        """
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,
        )
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
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    logger.warning(f"Request failed, retrying in {backoff}s: {exc}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise SleeperAPIError(f"Request failed after {self.max_retries} retries: {exc}") from exc

            # Retry rate limits and transient server errors. 5xx used to be
            # retried by the adapter's urllib3 Retry; it is handled here now so
            # there is exactly one retry layer.
            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                # A Retry-After from the server outranks our local schedule --
                # backing off less than the server asked just burns attempts
                # against a door that is still closed. urllib3's Retry honored
                # this for 5xx (respect_retry_after_header defaults to True),
                # so keeping it preserves behavior; 429 never reached that Retry
                # at all, since it was not in status_forcelist, so rate limits
                # gain the handling they never had.
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))

                if retry_after is not None and retry_after > MAX_RETRY_AFTER_SECONDS:
                    logger.warning(
                        f"Got {response.status_code} with Retry-After {retry_after:.0f}s, "
                        f"beyond the {MAX_RETRY_AFTER_SECONDS:.0f}s this client will wait"
                    )
                    if response.status_code == 429:
                        raise RateLimitError(
                            f"Rate limited; server asked for {retry_after:.0f}s, "
                            f"longer than the {MAX_RETRY_AFTER_SECONDS:.0f}s maximum wait"
                        )
                    raise SleeperAPIError(
                        f"Error {response.status_code}: server asked for a "
                        f"{retry_after:.0f}s retry delay, longer than the "
                        f"{MAX_RETRY_AFTER_SECONDS:.0f}s maximum wait",
                        status_code=response.status_code
                    )

                delay = retry_after if retry_after is not None else backoff
                logger.warning(
                    f"Got {response.status_code}, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                    + (" per Retry-After" if retry_after is not None else "")
                )
                time.sleep(delay)
                backoff *= 2  # Exponential backoff, for attempts with no header
                continue

            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded after all retries")

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
