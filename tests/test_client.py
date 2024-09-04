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
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        # Call the client.get method
        response = self.client.get('some-endpoint')
        
        # Assert that the response matches the expected value
        self.assertEqual(response, {"key": "value"})
        
        # Ensure that the session.request was called with the correct parameters
        mock_request.assert_called_with(
            method='GET',
            url=self.client.base_url + '/some-endpoint',
            params=None,
            json=None,
            timeout=self.client.timeout
        )

    @patch('sleeper_api.client.requests.Session.request')
    def test_get_request_failure(self, mock_request):
        # Mock a failed API response with a 404 status code
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        # Expect the SleeperAPIError to be raised
        with self.assertRaises(SleeperAPIError) as context:
            self.client.get('invalid-endpoint')

        # Verify that the exception contains the correct message
        self.assertIn("Error 404", str(context.exception))

        # Ensure that the session.request was called with the correct parameters
        mock_request.assert_called_with(
            method='GET',
            url=self.client.base_url + '/invalid-endpoint',
            params=None,
            json=None,
            timeout=self.client.timeout
        )

if __name__ == '__main__':
    unittest.main()
