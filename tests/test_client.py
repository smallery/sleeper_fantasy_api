import unittest
from unittest.mock import patch, Mock
from sleeper_api.client import SleeperClient
from sleeper_api.exceptions import SleeperAPIError


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

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_500_raises_error(self, mock_request):
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
