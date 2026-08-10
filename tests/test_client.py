import unittest
from unittest.mock import patch, Mock
from sleeper_api.client import SleeperClient
from sleeper_api.exceptions import SleeperAPIError, RateLimitError


class TestSleeperClient(unittest.TestCase):

    def setUp(self):
        self.client = SleeperClient()

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_success(self, mock_request):
        # Mock a successful API response
        mock_response = Mock()
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
        mock_response_500.status_code = 500
        mock_response_500.ok = False
        mock_response_500.text = "Internal Server Error"

        mock_response_200 = Mock()
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
        mock_response.status_code = 503
        mock_response.ok = False
        mock_response.text = "Service Unavailable"
        mock_request.return_value = mock_response

        with self.assertRaises(SleeperAPIError):
            self.client.get('down-endpoint')

        self.assertEqual(mock_request.call_count, self.client.max_retries + 1)

    def test_adapter_does_not_add_its_own_retries(self):
        # The single retry layer lives in _request; the adapter must not stack
        # another one underneath it.
        adapter = self.client.session.get_adapter('https://api.sleeper.app/v1/')
        self.assertEqual(adapter.max_retries.total, 0)

    @patch('sleeper_api.client.time.sleep')
    @patch('sleeper_api.client.requests.Session.request')
    def test_backoff_is_exponential(self, mock_request, mock_sleep):
        mock_response = Mock()
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
        mock_response_429.status_code = 429
        mock_response_429.ok = False

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.ok = True
        mock_response_200.json.return_value = {"key": "value"}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        # Should retry and succeed
        response = self.client.get('test-endpoint')
        self.assertEqual(response, {"key": "value"})

        # Should have slept once for retry
        mock_sleep.assert_called_once()


if __name__ == '__main__':
    unittest.main()
