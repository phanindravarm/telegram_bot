from unittest.mock import patch
from commands.worldtime import handle_worldtime


@patch("commands.worldtime.send_message")
def test_handle_worldtime(mock_send):
    handle_worldtime(123, "")
    mock_send.assert_called_once()
    text = mock_send.call_args[0][1]
    for label in ["IST", "UTC", "EST", "PST", "GMT", "CET", "JST", "AEST"]:
        assert label in text, f"{label} not found in worldtime output"
