"""
This module provides the `SleeperClient` class for interacting with the Sleeper API.

The `SleeperClient` class facilitates making API calls to various endpoints of the Sleeper API.
It supports handling HTTP requests and responses, including managing authentication
headers and timeouts.

"""
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import requests
from requests.adapters import HTTPAdapter

from .config import BASE_URL, CONVERT_RESULTS
from .exceptions import RateLimitError, SleeperAPIError

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

    Lifecycle: the client owns a ``requests.Session`` (and its connection
    pool) for as long as it is alive, and nothing closes that automatically
    on a deterministic schedule -- in CPython it happens whenever the garbage
    collector gets to it, which can be arbitrarily late once the client is
    captured by a closure or held as a module-level singleton. Use it as a
    context manager for short-lived usage (scripts, tests, one-off calls), or
    call :meth:`close` explicitly when a long-lived client (e.g. one held for
    a service's lifetime) is done. See the README for both patterns -- the
    long-lived pattern is the one to reach for when performance matters, since
    a warm connection pool is what makes concurrent fan-out
    (``max_workers=...``) fast.
    """
    def __init__(
        self,
        timeout = 10,
        max_retries = 3,
        initial_backoff = 1.0,
        convert_results: bool = CONVERT_RESULTS,
    ):
        """
        Initialize the SleeperClient.

        :param timeout: Timeout for requests in seconds.
        :param max_retries: Maximum retry attempts for rate-limited requests.
        :param initial_backoff: Initial backoff time in seconds for exponential backoff.
        :param convert_results: Default for every endpoint method's own
            ``convert_results`` parameter -- True (default) returns model
            objects (e.g. ``LeagueModel``), False returns raw JSON
            (``dict``/``list``). Set once here instead of passing
            ``convert_results=`` to every call; a call that still passes it
            explicitly overrides this client-level default for just that
            call. See issue #24: this replaces a rejected module-global
            design (see ``sleeper_api.config``) specifically so two clients
            in one process -- or concurrent callers sharing one client, e.g.
            ``get_season_projections(max_workers=...)`` -- can't silently
            fight over one setting.
        """
        self.base_url = BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.convert_results = convert_results
        self.session = self._create_session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        # Tracked separately from the session: requests.Session.close() only
        # clears the underlying connection pools, it does not stop the
        # session from being used again -- a closed adapter happily opens a
        # fresh socket on the next request. Without this flag, close() would
        # be a performance hint at best, silently defeating its own purpose
        # (and the caller's intent to release resources) the moment anything
        # made one more call.
        self._closed = False

    def close(self) -> None:
        """
        Release the underlying HTTP session and its connection pool.

        Idempotent -- calling this more than once (or on a client that was
        never used) is a no-op after the first call.
        """
        if self._closed:
            return
        self.session.close()
        self._closed = True

    def __enter__(self) -> "SleeperClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        # Always close on the way out, including when the with-block raised.
        # Returning False (not the exception) means we never suppress it --
        # closing the connection is a cleanup step, not error handling.
        self.close()
        return False

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
        :raises RuntimeError: If the client has been closed. requests.Session
            does not enforce this itself -- a closed adapter just opens a new
            socket on the next call, silently undoing close() -- so this
            client raises explicitly rather than let a closed client keep
            working by accident (e.g. after a service thinks it has shut
            its client down).
        """
        if self._closed:
            raise RuntimeError(
                "SleeperClient is closed; create a new client instead of "
                "reusing one after close() or exiting its `with` block."
            )

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

    def get(self, endpoint, params=None) -> Any:
        """
        Make a GET request. Currently sleeper API only supports reading.

        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :return: Parsed JSON response.
        """
        return self._request('GET', endpoint, params=params)

    def get_base_url(self) -> str:
        "Returns the base url"
        return self.base_url
