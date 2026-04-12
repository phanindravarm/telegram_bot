from unittest.mock import patch, MagicMock


@patch("commands.weather.send_message")
def test_handle_weather_no_args(mock_send):
    from commands.weather import handle_weather

    handle_weather(123, "")

    mock_send.assert_called_once()
    assert "usage" in mock_send.call_args[0][1].lower()


@patch("commands.weather.send_message")
@patch("commands.weather.requests.get")
def test_handle_weather_success(mock_get, mock_send):
    from commands.weather import handle_weather

    mock_response = MagicMock()
    mock_response.text = "London: +15°C"
    mock_get.return_value = mock_response

    handle_weather(123, "London")

    mock_get.assert_called_once_with("https://wttr.in/London?format=3", timeout=5)
    mock_send.assert_called_once_with(123, "London: +15°C")


@patch("commands.weather.send_message")
@patch("commands.weather.requests.get", side_effect=Exception("timeout"))
def test_handle_weather_api_failure(mock_get, mock_send):
    from commands.weather import handle_weather

    handle_weather(123, "London")

    mock_send.assert_called_once()
    assert "could not" in mock_send.call_args[0][1].lower()
