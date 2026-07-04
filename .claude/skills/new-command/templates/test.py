from unittest.mock import patch
from commands.COMMAND_NAME import handle_COMMAND_NAME


@patch("commands.COMMAND_NAME.send_message")
def test_handle_COMMAND_NAME(mock_send):
    handle_COMMAND_NAME(123, "")
    mock_send.assert_called_once()
