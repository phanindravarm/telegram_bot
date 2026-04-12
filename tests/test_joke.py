from unittest.mock import patch, MagicMock


@patch("commands.joke.send_message")
@patch("commands.joke.requests.get")
def test_handle_joke_success(mock_get, mock_send):
    from commands.joke import handle_joke

    mock_response = MagicMock()
    mock_response.json.return_value = {"setup": "Why did the chicken?", "punchline": "To get to the other side"}
    mock_get.return_value = mock_response

    handle_joke(123, "")

    mock_send.assert_called_once_with(123, "Why did the chicken?\n\nTo get to the other side")


@patch("commands.joke.send_message")
@patch("commands.joke.requests.get", side_effect=Exception("timeout"))
def test_handle_joke_api_failure(mock_get, mock_send):
    from commands.joke import handle_joke

    handle_joke(123, "")

    mock_send.assert_called_once()
    assert "could not" in mock_send.call_args[0][1].lower()
