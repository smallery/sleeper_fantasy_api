import threading
import time
import unittest
from unittest.mock import Mock, patch

from sleeper_api.client import SleeperClient, _parse_retry_after
from sleeper_api.exceptions import RateLimitError, SleeperAPIError


class TestSleeperClient(unittest.TestCase):

    def setUp(self):
        self.client = SleeperClient()

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_success(self, mock_request):
        # Mock a successful API response
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        # Call the client.get method
        response = self.client.get('some-endpoint')

        # Assert that the response matches the expected value
        self.assertEqual(response, {"key": "value"})

        # Ensure that the session.request was called with the correct parameters
        mock_request.assert_called_with(
            method='GET',
            url=self.client.base_url + 'some-endpoint',
            params=None,
            json=None,
            timeout=self.client.timeout
        )

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_404_returns_none(self, mock_request):
        # Mock a 404 response (graceful handling - returns None instead of error)
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        # 404 should return None instead of raising an error
        response = self.client.get('invalid-endpoint')
        self.assertIsNone(response)

        # Ensure that the session.request was called with the correct parameters
        mock_request.assert_called_with(
            method='GET',
            url=self.client.base_url + 'invalid-endpoint',
            params=None,
            json=None,
            timeout=self.client.timeout
        )

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_500_raises_error(self, mock_request, mock_sleep):
        # Mock a failed API response with a 500 status code
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        # Expect the SleeperAPIError to be raised for non-404 errors
        with self.assertRaises(SleeperAPIError) as context:
            self.client.get('error-endpoint')

        # Verify that the exception contains the correct message
        self.assertIn("Error 500", str(context.exception))

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_transient_500_is_retried_then_succeeds(self, mock_request, mock_sleep):
        # 5xx retries used to live in the adapter's urllib3 Retry. They are now
        # handled by _request, so they are visible at the Session.request level.
        mock_response_500 = Mock()
        mock_response_500.headers = {}
        mock_response_500.status_code = 500
        mock_response_500.ok = False
        mock_response_500.text = "Internal Server Error"

        mock_response_200 = Mock()
        mock_response_200.headers = {}
        mock_response_200.status_code = 200
        mock_response_200.ok = True
        mock_response_200.json.return_value = {"key": "value"}

        mock_request.side_effect = [mock_response_500, mock_response_200]

        self.assertEqual(self.client.get('flaky-endpoint'), {"key": "value"})
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once_with(self.client.initial_backoff)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_retries_are_bounded_by_max_retries(self, mock_request, mock_sleep):
        # Exactly max_retries + 1 requests should leave _request. This covers
        # the loop only -- it mocks Session.request, so the adapter is bypassed.
        # test_adapter_does_not_add_its_own_retries covers the other layer.
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 503
        mock_response.ok = False
        mock_response.text = "Service Unavailable"
        mock_request.return_value = mock_response

        with self.assertRaises(SleeperAPIError):
            self.client.get('down-endpoint')

        self.assertEqual(mock_request.call_count, self.client.max_retries + 1)

    def test_api_key_constructor_argument_was_removed(self):
        # Sleeper's read API needs no authentication -- api_key was accepted,
        # stored, and set an Authorization header, but nothing ever needed
        # it. Keeping an unused public parameter implies a capability the
        # API does not have, so it was removed rather than documented as a
        # no-op (see issue #21). This is a breaking change for 0.5.0.
        with self.assertRaises(TypeError):
            SleeperClient(api_key="unused")

    def test_no_authorization_header_is_set(self):
        self.assertNotIn('Authorization', self.client.session.headers)

    def test_adapter_does_not_add_its_own_retries(self):
        # The single retry layer lives in _request; the adapter must not stack
        # another one underneath it.
        adapter = self.client.session.get_adapter('https://api.sleeper.app/v1/')
        self.assertEqual(adapter.max_retries.total, 0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_backoff_is_exponential(self, mock_request, mock_sleep):
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 429
        mock_response.ok = False
        mock_response.text = "Too Many Requests"
        mock_request.return_value = mock_response

        with self.assertRaises(RateLimitError):
            self.client.get('rate-limited-endpoint')

        self.assertEqual(
            [call.args[0] for call in mock_sleep.call_args_list],
            [1.0, 2.0, 4.0],
        )

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_rate_limit_retry(self, mock_request, mock_sleep):
        # Mock rate limit on first call, success on second
        mock_response_429 = Mock()
        mock_response_429.headers = {}
        mock_response_429.status_code = 429
        mock_response_429.ok = False

        mock_response_200 = Mock()
        mock_response_200.headers = {}
        mock_response_200.status_code = 200
        mock_response_200.ok = True
        mock_response_200.json.return_value = {"key": "value"}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        # Should retry and succeed
        response = self.client.get('test-endpoint')
        self.assertEqual(response, {"key": "value"})

        # Should have slept once for retry
        mock_sleep.assert_called_once()

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_raw_returns_bytes_not_parsed_json(self, mock_request):
        # get_raw() exists so a caller (PersistentCache.set_bytes(), via
        # ProjectionsEndpoint) can persist exactly what the server sent --
        # see issue #15. It must return the raw body, and must NOT call
        # response.json() at all (that would defeat the point: parsing just
        # to discard the result).
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.content = b'{"key": "value"}'
        mock_request.return_value = mock_response

        result = self.client.get_raw('some-endpoint')

        self.assertEqual(result, b'{"key": "value"}')
        mock_response.json.assert_not_called()
        mock_request.assert_called_with(
            method='GET',
            url=self.client.base_url + 'some-endpoint',
            params=None,
            json=None,
            timeout=self.client.timeout
        )

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_raw_404_returns_none(self, mock_request):
        # Matches get()'s contract: a missing resource is not an error.
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        self.assertIsNone(self.client.get_raw('invalid-endpoint'))

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_get_raw_error_status_raises(self, mock_request, mock_sleep):
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with self.assertRaises(SleeperAPIError) as context:
            self.client.get_raw('error-endpoint')

        self.assertIn("Error 500", str(context.exception))

    def test_get_keeps_its_existing_signature_and_return_type(self):
        # Explicit acceptance check from issue #15: adding get_raw() must not
        # change get()'s public contract.
        import inspect
        sig = inspect.signature(SleeperClient.get)
        self.assertEqual(list(sig.parameters), ['self', 'endpoint', 'params'])


class TestRetryAfter(unittest.TestCase):
    """Retry-After handling in the consolidated retry loop.

    urllib3's Retry honored Retry-After for the codes in status_forcelist
    (respect_retry_after_header defaults to True), so dropping that adapter
    would have silently lost the behavior for 5xx. 429 was never in the
    forcelist, so rate limits never had it at all.
    """

    def setUp(self):
        self.client = SleeperClient()

    @staticmethod
    def _response(status, retry_after=None, ok=False):
        r = Mock()
        r.status_code = status
        r.ok = ok
        r.text = "error"
        r.headers = {} if retry_after is None else {"Retry-After": retry_after}
        return r

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_retry_after_seconds_overrides_backoff(self, mock_request, mock_sleep):
        ok = self._response(200, ok=True)
        ok.json.return_value = {"key": "value"}
        mock_request.side_effect = [self._response(429, "7"), ok]

        self.assertEqual(self.client.get('endpoint'), {"key": "value"})
        # 7s from the header, not the 1s local backoff.
        mock_sleep.assert_called_once_with(7.0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_retry_after_honored_for_5xx(self, mock_request, mock_sleep):
        ok = self._response(200, ok=True)
        ok.json.return_value = {"key": "value"}
        mock_request.side_effect = [self._response(503, "5"), ok]

        self.assertEqual(self.client.get('endpoint'), {"key": "value"})
        mock_sleep.assert_called_once_with(5.0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_retry_after_http_date_is_parsed(self, mock_request, mock_sleep):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime

        when = datetime.now(timezone.utc) + timedelta(seconds=20)
        ok = self._response(200, ok=True)
        ok.json.return_value = {"key": "value"}
        mock_request.side_effect = [
            self._response(429, format_datetime(when)), ok
        ]

        self.assertEqual(self.client.get('endpoint'), {"key": "value"})
        slept = mock_sleep.call_args[0][0]
        self.assertAlmostEqual(slept, 20.0, delta=2.0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_past_http_date_does_not_sleep_negative(self, mock_request, mock_sleep):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime

        when = datetime.now(timezone.utc) - timedelta(seconds=30)
        ok = self._response(200, ok=True)
        ok.json.return_value = {"key": "value"}
        mock_request.side_effect = [
            self._response(503, format_datetime(when)), ok
        ]

        self.assertEqual(self.client.get('endpoint'), {"key": "value"})
        self.assertGreaterEqual(mock_sleep.call_args[0][0], 0.0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_unparseable_retry_after_falls_back_to_backoff(self, mock_request, mock_sleep):
        ok = self._response(200, ok=True)
        ok.json.return_value = {"key": "value"}
        mock_request.side_effect = [self._response(429, "not-a-date"), ok]

        self.assertEqual(self.client.get('endpoint'), {"key": "value"})
        mock_sleep.assert_called_once_with(self.client.initial_backoff)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_excessive_retry_after_raises_without_sleeping(self, mock_request, mock_sleep):
        # Sleeping 10 minutes inside a web request handler is worse than
        # failing fast, and retrying sooner than asked would be worse still.
        mock_request.return_value = self._response(429, "600")

        with self.assertRaises(RateLimitError) as ctx:
            self.client.get('endpoint')

        mock_sleep.assert_not_called()
        self.assertEqual(mock_request.call_count, 1)
        self.assertIn("600s", str(ctx.exception))

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_excessive_retry_after_on_5xx_raises_api_error(self, mock_request, mock_sleep):
        mock_request.return_value = self._response(503, "600")

        with self.assertRaises(SleeperAPIError) as ctx:
            self.client.get('endpoint')

        mock_sleep.assert_not_called()
        self.assertEqual(ctx.exception.status_code, 503)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_retry_after_does_not_apply_to_success_or_404(self, mock_request, mock_sleep):
        # A Retry-After on a non-retryable status must be ignored entirely.
        mock_request.return_value = self._response(404, "300")

        self.assertIsNone(self.client.get('endpoint'))
        mock_sleep.assert_not_called()


class TestClientLifecycle(unittest.TestCase):
    """close() / context-manager support -- see GitHub issue #22."""

    def setUp(self):
        self.client = SleeperClient()

    def test_close_closes_the_session(self):
        with patch.object(self.client.session, 'close') as mock_close:
            self.client.close()
            mock_close.assert_called_once()
        self.assertTrue(self.client._closed)

    def test_close_is_idempotent(self):
        # Calling close() twice must not call session.close() twice -- a
        # caller that closes defensively (e.g. in both a `finally` and an
        # outer context manager) should not be punished for it.
        with patch.object(self.client.session, 'close') as mock_close:
            self.client.close()
            self.client.close()
            mock_close.assert_called_once()

    def test_with_statement_closes_session_on_clean_exit(self):
        with self.client as client:
            self.assertIs(client, self.client)
            self.assertFalse(self.client._closed)
        self.assertTrue(self.client._closed)

    def test_exception_inside_with_block_propagates_and_still_closes(self):
        with self.assertRaises(ValueError):
            with self.client:
                raise ValueError("boom")
        self.assertTrue(self.client._closed)

    def test_enter_returns_the_client_itself(self):
        with self.client as client:
            self.assertIs(client, self.client)

    @patch('sleeper_api.client.requests.Session.request')
    def test_request_after_close_raises_clear_error(self, mock_request):
        # requests.Session does not itself error on reuse after close() -- an
        # adapter just opens a fresh socket -- so this client raises
        # explicitly instead of silently reopening connections a caller
        # believed were released.
        self.client.close()
        with self.assertRaises(RuntimeError) as ctx:
            self.client.get('some-endpoint')
        self.assertIn("closed", str(ctx.exception))
        mock_request.assert_not_called()

    @patch('sleeper_api.client.requests.Session.request')
    def test_close_during_backoff_aborts_remaining_retries(self, mock_request):
        """Issue #30: close() landing while a request is asleep between
        retries must stop the retry loop instead of letting it wake up and
        open a fresh connection on a session whose owner already tore it
        down.

        Deterministic via thread-coordination events, not sleep-based timing
        races: the patched time.sleep() signals that the request has entered
        its backoff window, blocks a background thread does close() and
        signals back, and only then does the patched sleep return -- so the
        interleaving (close() lands strictly between attempt 1 and the retry
        that would otherwise be attempt 2) is guaranteed on every run.
        """
        client = SleeperClient(max_retries=3, initial_backoff=0.01)

        retryable = Mock()
        retryable.headers = {}
        retryable.status_code = 503
        retryable.ok = False
        retryable.text = "Service Unavailable"
        mock_request.return_value = retryable

        entered_backoff = threading.Event()
        closed = threading.Event()

        def fake_sleep(_seconds):
            entered_backoff.set()
            # Do not return (and let the loop retry) until close() has
            # actually landed from the other thread.
            self.assertTrue(closed.wait(timeout=5), "closer thread never ran")

        def closer():
            self.assertTrue(
                entered_backoff.wait(timeout=5),
                "request never reached the backoff window"
            )
            client.close()
            closed.set()

        closer_thread = threading.Thread(target=closer)

        with patch('sleeper_api.client.time.sleep', side_effect=fake_sleep):
            closer_thread.start()
            with self.assertRaises(RuntimeError) as ctx:
                client.get('flaky-endpoint')
            closer_thread.join(timeout=5)

        self.assertIn("closed", str(ctx.exception))
        self.assertFalse(closer_thread.is_alive())
        # Exactly one request went out (the one that got the 503 and hit the
        # backoff where close() landed). The bug this guards against is a
        # second (or third, or fourth) request going out after close().
        self.assertEqual(mock_request.call_count, 1)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_close_before_any_retry_still_raises_on_entry(self, mock_request, mock_sleep):
        # The entry check and the recheck-per-iteration in #30's fix share
        # one code path (_check_not_closed). This confirms that sharing it
        # didn't change entry-check behavior: a client closed before the
        # call is made still raises immediately, with no request attempted.
        self.client.close()
        with self.assertRaises(RuntimeError):
            self.client.get('some-endpoint')
        mock_request.assert_not_called()
        mock_sleep.assert_not_called()


class TestParseRetryAfter(unittest.TestCase):
    """Unit coverage for the header parser itself."""

    def test_absent_or_malformed_values_return_none(self):
        for value in (None, "", "   ", "abc", [], 12, object()):
            with self.subTest(value=value):
                self.assertIsNone(_parse_retry_after(value))

    def test_delta_seconds(self):
        self.assertEqual(_parse_retry_after("30"), 30.0)
        self.assertEqual(_parse_retry_after(" 30 "), 30.0)
        self.assertEqual(_parse_retry_after("0"), 0.0)

    def test_negative_delta_is_clamped_to_zero(self):
        self.assertEqual(_parse_retry_after("-5"), 0.0)


if __name__ == '__main__':
    unittest.main()


class TestCloseRaceWithInFlightRequest(unittest.TestCase):
    """close() lifecycle: no request may start after close, and the drain is opt-in.

    Checking `_closed` and starting the request used to be two separate steps,
    so close() could complete in the gap and requests would open a fresh socket
    on the closed adapter. Draining in-flight work fixes that fully, but it must
    not be the default -- the documented `with SleeperClient()` +
    asyncio.to_thread pattern unwinds the context manager on the event loop, so
    a blocking drain there would stall every other task on that loop.
    """

    def _parked_client(self):
        """A client whose next request blocks until the returned event is set."""
        client = SleeperClient()
        entered, release, saw = threading.Event(), threading.Event(), []

        def slow_request(*a, **k):
            entered.set()
            release.wait(5)
            saw.append(client.session.adapters == {})
            r = Mock()
            r.status_code, r.ok, r.headers = 200, True, {}
            r.json.return_value = {"ok": True}
            return r

        client.session.request = slow_request
        return client, entered, release, saw

    def test_close_does_not_block_by_default(self):
        # The event-loop safety property: unwinding a `with` block must not
        # wait on a worker thread's request.
        client, entered, release, _ = self._parked_client()
        worker = threading.Thread(target=lambda: client.get("state/nfl"))
        worker.start()
        self.assertTrue(entered.wait(5))

        t0 = time.monotonic()
        client.close()
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5, "default close() blocked on an in-flight request")

        release.set()
        worker.join(5)

    def test_close_with_drain_waits_for_the_in_flight_request(self):
        client, entered, release, saw = self._parked_client()
        worker = threading.Thread(target=lambda: client.get("state/nfl"))
        worker.start()
        self.assertTrue(entered.wait(5))

        closer = threading.Thread(target=lambda: client.close(drain=5))
        closer.start()
        closer.join(timeout=0.3)
        self.assertTrue(closer.is_alive(), "close(drain=...) returned mid-flight")

        release.set()
        worker.join(5)
        closer.join(5)
        self.assertFalse(closer.is_alive())
        self.assertEqual(saw, [False], "session released before the request finished")

    def test_second_draining_close_waits_for_the_first_to_release(self):
        # `_closed` only means "no new requests" -- a second caller that asked
        # to wait must wait for the session to actually be released.
        client, entered, release, _ = self._parked_client()
        worker = threading.Thread(target=lambda: client.get("state/nfl"))
        worker.start()
        self.assertTrue(entered.wait(5))

        first = threading.Thread(target=lambda: client.close(drain=5))
        first.start()
        time.sleep(0.1)                      # let `first` claim the close
        second_returned = threading.Event()

        def second_close():
            client.close(drain=5)
            second_returned.set()

        threading.Thread(target=second_close).start()
        self.assertFalse(second_returned.wait(0.3),
                         "second close(drain=...) returned before the session was released")

        release.set()
        worker.join(5)
        first.join(5)
        self.assertTrue(second_returned.wait(5))

    def test_drain_is_bounded(self):
        client, entered, release, _ = self._parked_client()
        worker = threading.Thread(target=lambda: client.get("state/nfl"))
        worker.start()
        self.assertTrue(entered.wait(5))

        t0 = time.monotonic()
        client.close(drain=0.2)
        self.assertLess(time.monotonic() - t0, 2.0, "close() ignored its drain budget")

        release.set()
        worker.join(5)

    def test_request_starting_after_close_is_refused(self):
        client = SleeperClient()
        client.close()
        with self.assertRaises(RuntimeError):
            client.get("state/nfl")


class TestDeferredSessionRelease(unittest.TestCase):
    """A non-blocking close() must not release the session under a registered attempt.

    Atomic registration only helps a *draining* close. With the zero-drain
    default, a thread could register `_inflight`, be descheduled before
    session.request(), and have close() release the session underneath it --
    the resumed attempt then builds a fresh pool, opening a socket after
    close() returned. The last request out releases the session instead.
    """

    def test_default_close_defers_release_to_the_last_request(self):
        client = SleeperClient()
        registered = threading.Event()
        resume = threading.Event()
        observed = {}

        real_request = client.session.request

        def parked_request(*a, **k):
            # Stand in for a thread descheduled between registering and
            # actually issuing the request.
            registered.set()
            resume.wait(5)
            observed["adapters_at_request"] = dict(client.session.adapters)
            r = Mock()
            r.status_code, r.ok, r.headers = 200, True, {}
            r.json.return_value = {"ok": True}
            return r

        client.session.request = parked_request
        worker = threading.Thread(target=lambda: client.get("state/nfl"))
        worker.start()
        self.assertTrue(registered.wait(5))

        t0 = time.monotonic()
        client.close()                       # default: must not block
        self.assertLess(time.monotonic() - t0, 0.5, "default close() blocked")
        self.assertFalse(client._released, "session released while a request was registered")

        resume.set()
        worker.join(5)
        self.assertTrue(observed["adapters_at_request"], "adapters were cleared mid-request")
        # The last request out completes the release.
        self.assertTrue(client._released, "last request did not release the session")
        self.assertIsNot(real_request, None)

    def test_close_with_nothing_in_flight_releases_immediately(self):
        client = SleeperClient()
        client.close()
        self.assertTrue(client._released)
