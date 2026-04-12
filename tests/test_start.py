from unittest.mock import patch


@patch("commands.start.send_message")
def test_handle_start_sends_welcome_with_help(mock_send):
    from commands.start import handle_start

    handle_start(123, "")

    mock_send.assert_called_once()
    args = mock_send.call_args
    assert args[0][0] == 123
    assert "/help" in args[0][1]
