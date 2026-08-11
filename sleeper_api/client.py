"""
This module provides the `SleeperClient` class for interacting with the Sleeper API.

The `SleeperClient` class facilitates making API calls to various endpoints of the Sleeper API.
It supports handling HTTP requests and responses, including managing authentication
headers and timeouts.

"""
import logging
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Literal, Optional

import requests
from requests.adapters import HTTPAdapter

from .config import BASE_URL, CONVERT_RESULTS
from .exceptions import RateLimitError, SleeperAPIError

logger = logging.getLogger(__name__)

# Default upper bound for close(drain=...) when a caller opts into waiting.
# Bounded so a hung request cannot make close() block forever.
CLOSE_DRAIN_TIMEOUT_SECONDS = 30.0

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

        # Guards `_closed` and `_inflight` together. Checking `_closed`
        # and registering the request has to be one atomic step: with a
        # bare flag read, close() could complete in the gap between the
        # check and session.request(), and requests would then open a
        # fresh socket on the closed adapter -- the very thing the flag
        # exists to prevent. The lock is released before the HTTP call so
        # concurrent requests still overlap; only the bookkeeping is
        # serialized.
        self._lifecycle = threading.Condition()
        self._inflight = 0
        self._released = False
        self._release_pending = False

    def close(self, drain: float = 0.0) -> None:
        """
        Release the underlying HTTP session and its connection pool.

        Returns immediately by default. Marking the client closed already
        stops any *new* request from starting (see :meth:`_request`), so the
        common case needs no waiting.

        :param drain: Seconds to wait for requests already on the wire to
            finish before releasing the session. Defaults to 0 -- **do not
            raise it on a thread you cannot afford to block**. In particular
            the documented `with SleeperClient()` + ``asyncio.to_thread``
            pattern unwinds the context manager on the event loop itself, so
            a blocking drain there would stall every other task on that loop
            for the duration -- defeating the point of moving the call to a
            worker thread. Capped at CLOSE_DRAIN_TIMEOUT_SECONDS.

        Idempotent. A caller that passes ``drain`` while another thread is
        already closing waits for that close to actually release the session,
        rather than returning early on a flag that only means "closing".
        """
        wait_budget = min(max(drain, 0.0), CLOSE_DRAIN_TIMEOUT_SECONDS)

        with self._lifecycle:
            if self._closed:
                # Someone else is closing, or already has. `_closed` alone
                # only means "no new requests"; the session may still be in
                # the process of being released, so a caller that asked to
                # wait must wait for `_released`, not for the flag it already
                # sees set.
                if wait_budget:
                    self._wait_until(lambda: self._released, wait_budget)
                return

            self._closed = True
            if wait_budget:
                self._wait_until(lambda: self._inflight == 0, wait_budget)

            if self._inflight:
                # Requests are still registered. Releasing the session now
                # would let a thread that registered but has not yet reached
                # session.request() resume against closed adapters, which
                # simply builds a fresh pool -- a new socket opened after
                # close() returned. Hand the release to whichever request
                # leaves last, so the caller is never blocked and the session
                # still outlives every attempt that claimed it.
                self._release_pending = True
                logger.debug(
                    f"close() deferring session release to the last of "
                    f"{self._inflight} in-flight request(s)"
                )
                return

        self._release()

    def _release(self):
        """
        Close the session and wake anything waiting on `_released`.

        Called outside `_lifecycle` -- either by close() when nothing is in
        flight, or by the last request to deregister after a deferred close.
        """
        self.session.close()
        with self._lifecycle:
            self._release_pending = False
            self._released = True
            self._lifecycle.notify_all()

    def _wait_until(self, predicate, budget):
        """
        Wait for `predicate` under `_lifecycle`, up to `budget` seconds.

        :return: True if the predicate held before the budget ran out.
        """
        deadline = time.monotonic() + budget
        while not predicate():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._lifecycle.wait(remaining)
        return True

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

    def _handle_response(self, response, raw: bool = False):
        """
        Handle the API response.

        :param response: The HTTP response object.
        :param raw: If True, return the raw response body (``bytes``)
            instead of parsing it as JSON. Used by :meth:`get_raw` so a
            caller that wants to persist the response (e.g. a cache) can
            write exactly what the server sent, without this client decoding
            it to a dict that the caller would otherwise have to re-encode
            back to bytes. See issue #15.
        :return: The parsed JSON data (or raw bytes, if ``raw``) or raise an
            error.
        """
        if response.status_code == 404:
            return None  # Not an error, just missing resource

        if not response.ok:
            raise SleeperAPIError(
                f"Error {response.status_code}: {response.text}",
                status_code=response.status_code
            )
        if raw:
            return response.content
        try:
            return response.json()
        except ValueError as exc:
            raise SleeperAPIError("Invalid JSON response received") from exc

    def _check_not_closed(self):
        """
        Raise if the client has been closed.

        Shared by the entry check and the top of every retry iteration in
        :meth:`_request` (see there for why both matter), so the two can
        never diverge in behavior or message.

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

    def _request(self, method, endpoint, params=None, data=None, raw=False):
        """
        Make a request to the Sleeper API with retry logic.

        :param method: HTTP method (GET, POST, etc.).
        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :param data: Request payload for POST/PUT requests.
        :param raw: If True, return the raw response body (bytes) instead of
            parsed JSON. See :meth:`get_raw`.
        :return: Parsed JSON response (or raw bytes, if ``raw``).
        :raises RuntimeError: If the client is closed. Checked on entry *and*
            again at the top of every retry iteration -- not just once --
            because `close()` can land from another thread (or an
            `asyncio.to_thread` caller that got cancelled and unwound a
            `with SleeperClient()` block) while this call is asleep in
            `time.sleep(backoff)` between attempts. Without the recheck, a
            request that had already passed the entry check could wake up
            and open a fresh connection after the session was supposed to be
            gone -- the exact thing the guard exists to prevent. Aborting
            mid-retry raises the same `RuntimeError` as the entry check
            (rather than a distinct error type), since both represent the
            same fact from the caller's point of view: this client is closed,
            stop using it. See issue #30.
        """
        url = f'{self.base_url}{endpoint}'
        backoff = self.initial_backoff

        for attempt in range(self.max_retries + 1):
            # Atomically confirm the client is open and register this
            # attempt, so close() cannot slip in between the two.
            with self._lifecycle:
                self._check_not_closed()
                self._inflight += 1
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
            finally:
                # Deregister as soon as the HTTP call returns, so a client
                # waiting in close() is not held up by this attempt's backoff
                # sleep -- only by work actually on the wire.
                with self._lifecycle:
                    self._inflight -= 1
                    self._lifecycle.notify_all()
                    # A close() that arrived while this attempt was registered
                    # left the session for the last one out to release.
                    release_now = self._release_pending and self._inflight == 0
                if release_now:
                    self._release()

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

            return self._handle_response(response, raw=raw)

    def get(self, endpoint, params=None) -> Any:
        """
        Make a GET request. Currently sleeper API only supports reading.

        :param endpoint: API endpoint (e.g., 'user/{user_id}').
        :param params: URL parameters.
        :return: Parsed JSON response.
        """
        return self._request('GET', endpoint, params=params)

    def get_raw(self, endpoint, params=None) -> Optional[bytes]:
        """
        Make a GET request, returning the raw response body instead of
        parsed JSON.

        Exists so a caller that wants to persist the response verbatim (e.g.
        :class:`~sleeper_api.persistent_cache.PersistentCache`, via
        :meth:`~sleeper_api.persistent_cache.PersistentCache.set_bytes`) can
        write exactly what the server sent, instead of this client decoding
        the body to a dict that the caller then has to re-encode back into
        bytes to store -- a decode-then-re-encode round trip that turned out
        to be the dominant cost of a cache write (see issue #15). Goes
        through the same retry/rate-limit handling as :meth:`get`; ``get()``
        keeps its existing signature and return type unchanged.

        :param endpoint: API endpoint (e.g., 'projections/nfl/regular/2025/1').
        :param params: URL parameters.
        :return: Raw response body as ``bytes``, or ``None`` for a 404
            (matching ``get()``'s contract for a missing resource).
        """
        return self._request('GET', endpoint, params=params, raw=True)

    def get_base_url(self) -> str:
        "Returns the base url"
        return self.base_url
