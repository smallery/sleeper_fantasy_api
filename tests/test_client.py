import unittest
from unittest.mock import patch, Mock
from sleeper_api.client import SleeperClient, _parse_retry_after
from sleeper_api.exceptions import SleeperAPIError, RateLimitError


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
        from email.utils import format_datetime
        from datetime import datetime, timedelta, timezone

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
        from email.utils import format_datetime
        from datetime import datetime, timedelta, timezone

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
